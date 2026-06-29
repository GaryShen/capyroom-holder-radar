"""每日入口:算今天 → 寫 store → 偵測 → (只在 alert 時)推播。"""
from holder_radar import store, judge


def run_daily(conn, cohort_source, notifier, as_of_date: str, price: float) -> list:
    """cohort_source.run() -> dict(5 個 cohort 欄位,不含 date/price)。"""
    prev = store.latest(conn)
    row = {**cohort_source.run(), "date": as_of_date, "price": price}
    store.upsert_cohort(conn, row)
    history = store.recent(conn, 90)
    sigs = judge.detect(row, prev or row, history)
    if notifier and any(s.level == "alert" for s in sigs):  # 省 LINE 額度:只推 alert
        notifier.send(sigs)
    return sigs


def main() -> None:  # pragma: no cover - 組裝真實依賴,需 GCP/LINE 憑證
    import os
    from holder_radar import prices
    from holder_radar.notify import LineAdapter
    from holder_radar.bigquery_cohort import run_cohort  # noqa: F401 (Task 2/3)

    conn = store.init_db(os.getenv("HOLDER_RADAR_DB", "data/snapshot.sqlite"))
    today = os.getenv("AS_OF_DATE") or __import__("datetime").date.today().isoformat()
    price = prices.current_btc_usd()
    # cohort_source: 薄 wrapper 把 BigQuery 包成 .run()(Task 2/3 完成後接上)
    raise SystemExit("接上 BigQuery cohort_source 後即可跑;見 README 自架步驟。")
