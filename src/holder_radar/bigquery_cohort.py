"""從 BigQuery 公開資料集算 LTH/STH 供給結構。

第一版:全量 outputs⋈inputs 找未花費 UTXO,依「上次移動時間」分齡。
⚠️ 很可能掃描 > 1TB → 先用 dry_run_scan_bytes 量測;超標就改增量/分區(見 README)。
成本線(已實現市值)是 Task 3,於本檔擴充。
"""
from google.cloud import bigquery
from holder_radar import config


def build_supply_query(as_of_date: str) -> str:
    return f"""
    DECLARE as_of TIMESTAMP DEFAULT TIMESTAMP('{as_of_date} 00:00:00');
    WITH unspent AS (
      SELECT o.value AS sats, o.block_timestamp AS born
      FROM `bigquery-public-data.crypto_bitcoin.outputs` o
      LEFT JOIN `bigquery-public-data.crypto_bitcoin.inputs` i
        ON o.transaction_hash = i.spent_transaction_hash
       AND o.index = i.spent_output_index
      WHERE i.spent_transaction_hash IS NULL
        AND o.block_timestamp <= as_of
    )
    SELECT
      SUM(IF(TIMESTAMP_DIFF(as_of, born, SECOND) >= {config.STH_MAX_AGE_SECONDS}, sats, 0)) / 1e8 AS lth_btc,
      SUM(IF(TIMESTAMP_DIFF(as_of, born, SECOND) <  {config.STH_MAX_AGE_SECONDS}, sats, 0)) / 1e8 AS sth_btc,
      SUM(sats) / 1e8 AS circulating_btc
    FROM unspent
    """


def dry_run_scan_bytes(client, sql: str) -> int:
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        dry_run=True, use_query_cache=False))
    return job.total_bytes_processed


def run_supply(client, as_of_date: str) -> dict:
    sql = build_supply_query(as_of_date)
    scanned = dry_run_scan_bytes(client, sql)
    if scanned >= config.FREE_SCAN_BYTES_LIMIT:
        raise RuntimeError(
            f"查詢掃描 {scanned / 1e12:.2f}TB ≥ 免費額度 1TB,需改增量/分區再跑")
    row = next(iter(client.query(sql).result()))
    return {"lth_btc": row.lth_btc, "sth_btc": row.sth_btc,
            "circulating_btc": row.circulating_btc}
