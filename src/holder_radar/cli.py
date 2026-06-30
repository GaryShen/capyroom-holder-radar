"""入口,兩條路:
- daily()    : 免費。抓現價、比上次存的成本線偵測跌穿、(alert才)推播、更新 data.js。不碰 BigQuery。
- snapshot() : BigQuery 全量更新 cohort(慢變數)。守 ≤2次/月——只手動/低頻觸發。
"""
import os
from holder_radar import store, judge, export


def daily(conn, notifier, price: float, price_by_date: dict, data_js_path: str) -> list:
    """免費每日路:cohort 沿用最近一次快照,只換今天的價格,偵測跌穿。"""
    latest = store.latest(conn)
    if not latest:
        raise SystemExit("尚無 cohort 快照,請先跑 snapshot()(BigQuery)。")
    prev = latest
    today = {k: latest[k] for k in
             ("lth_btc", "sth_btc", "circulating_btc", "sth_cost_basis", "lth_cost_basis")}
    today["date"] = max(price_by_date)        # 最新有價格的日期
    today["price"] = price
    store.upsert_cohort(conn, today)
    sigs = judge.detect(today, prev, store.recent(conn, 90))
    if notifier and any(s.level == "alert" for s in sigs):
        notifier.send(sigs)
    export.write_data_js(
        export.build_dashboard_data(price_by_date, store.recent(conn, 400), store.latest(conn)),
        data_js_path)
    return sigs


def snapshot(conn, cohort_source, as_of_date: str, price: float) -> dict:
    """BigQuery 全量更新 cohort（吃 ~0.45TB 額度，≤2次/月）。"""
    row = {**cohort_source.run(), "date": as_of_date, "price": price}
    store.upsert_cohort(conn, row)
    return row


def main() -> None:  # pragma: no cover - 組裝真實依賴,需 GCP/LINE 憑證
    import sys
    from holder_radar import prices
    db = os.getenv("HOLDER_RADAR_DB", "data/snapshot.sqlite")
    conn = store.init_db(db)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if cmd == "snapshot":
        # 防呆:snapshot 會跑 BigQuery 並計費(billing 帳號無免費額度時約 $7/次)。
        # 必須明確設旗標才准跑,避免不小心燒錢。Sandbox 帳號才真免費。
        if not os.getenv("HOLDER_RADAR_RUN_SNAPSHOT"):
            raise SystemExit(
                "snapshot 會跑 BigQuery 並可能計費(此帳號可能無免費額度)。\n"
                "確定要跑請設 HOLDER_RADAR_RUN_SNAPSHOT=1。")
        from google.cloud import bigquery
        from holder_radar import bigquery_cohort
        as_of = os.getenv("AS_OF_DATE") or __import__("datetime").date.today().isoformat()
        px = prices.daily_history(180)
        client = bigquery.Client()

        class _Src:
            def run(self):
                r = bigquery_cohort.run_cohort(client, as_of, px)
                r["lth_cost_basis"] = r.get("lth_cost_basis")  # 目前未算,留欄位
                return r
        snapshot(conn, _Src(), as_of, prices.current_btc_usd())
    else:  # daily
        from holder_radar.notify import LineAdapter
        px = prices.daily_history(180)
        notifier = (LineAdapter(os.environ["LINE_TOKEN"], os.environ["LINE_TO"])
                    if os.getenv("LINE_TOKEN") else None)
        daily(conn, notifier, prices.current_btc_usd(), px, "app/assets/data.js")
