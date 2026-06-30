"""從 BigQuery 公開資料集算 LTH/STH 供給 + STH 成本線。

分工:
- BigQuery 只做重活——掃鏈上資料,回「每個出生日還握著多少幣」(一張小表)。
- 價格加權 / cohort 分齡 / 成本線 全在 Python 純函式做(可測、不碰 GCP、不存東西)。

⚠️ breakdown 查詢的掃描量先用 dry_run_scan_bytes 量測(免費);單次約 0.45TB,
   每天跑會超 1TB/月 → 日常走增量(Task 4),種子只跑一次。
"""
from datetime import date, timedelta
from google.cloud import bigquery
from holder_radar import config


def build_age_breakdown_query(as_of_date: str) -> str:
    """回傳「未花費 UTXO 依出生日加總 BTC」的 SQL。結果 ~6000 列(date, btc)。

    ⚠️ 單一 SELECT 陳述式,**不可用 DECLARE**:DECLARE 會讓查詢變成 SCRIPT,
       parent+child 各計費一次 = 帳單翻倍。as_of 直接以字面值內聯。
    """
    return f"""
    WITH unspent AS (
      SELECT o.value AS sats, o.block_timestamp AS born
      FROM `bigquery-public-data.crypto_bitcoin.outputs` o
      LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
        ON o.transaction_hash = i.spent_transaction_hash
       AND o.index = i.spent_output_index
      WHERE i.spent_transaction_hash IS NULL
        AND o.block_timestamp <= TIMESTAMP('{as_of_date} 00:00:00')
    )
    SELECT DATE(born) AS d, SUM(sats) / 1e8 AS btc
    FROM unspent GROUP BY d ORDER BY d
    """


def cohort_metrics(breakdown: list[dict], as_of_date: str,
                   prices_by_date: dict[str, float]) -> dict:
    """純函式:把 (出生日→BTC) 分齡並算 STH 成本線。

    breakdown: [{"d": "YYYY-MM-DD", "btc": float}, ...]
    prices_by_date: {"YYYY-MM-DD": usd} —— 至少要涵蓋近 155 天(算 STH 成本線用)。
    回傳 lth_btc / sth_btc / circulating_btc / sth_cost_basis(None 表價格不足)。
    """
    boundary = date.fromisoformat(as_of_date) - timedelta(days=config.LTH_BOUNDARY_DAYS)
    lth = sth = circ = 0.0
    sth_value = sth_priced = 0.0  # 已實現市值 / 有對到價的 STH 量
    for r in breakdown:
        d, btc = date.fromisoformat(r["d"]), r["btc"]
        circ += btc
        if d <= boundary:
            lth += btc
        else:
            sth += btc
            p = prices_by_date.get(r["d"])
            if p is not None:
                sth_value += btc * p
                sth_priced += btc
    return {
        "lth_btc": lth,
        "sth_btc": sth,
        "circulating_btc": circ,
        "sth_cost_basis": (sth_value / sth_priced) if sth_priced else None,
    }


def dry_run_scan_bytes(client, sql: str) -> int:
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        dry_run=True, use_query_cache=False))
    return job.total_bytes_processed


def run_cohort(client, as_of_date: str, prices_by_date: dict[str, float]) -> dict:
    sql = build_age_breakdown_query(as_of_date)
    scanned = dry_run_scan_bytes(client, sql)
    if scanned >= config.FREE_SCAN_BYTES_LIMIT:
        raise RuntimeError(
            f"查詢掃描 {scanned / 1e12:.2f}TB ≥ 免費額度 1TB,需改增量/分區再跑")
    breakdown = [{"d": row.d.isoformat(), "btc": float(row.btc)}
                 for row in client.query(sql).result()]
    return cohort_metrics(breakdown, as_of_date, prices_by_date)
