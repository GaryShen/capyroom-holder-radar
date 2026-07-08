"""入口,兩條路:
- daily()    : 免費。抓現價 + 免費即時 cohort(bgeometrics)→ 偵測跌穿 → (alert才)推播 → 更新 data.js。不碰 BigQuery。
- snapshot() : BigQuery 全量自算 cohort(備援/驗證用)。會計費,預設不用,加防呆。
"""
import os
from holder_radar import store, judge, export


def daily(conn, notifier, price: float, price_by_date: dict, data_js_path: str,
          fresh_cohort: dict | None = None) -> list:
    """免費每日路:有 fresh_cohort(bgeometrics 即時)就用它,否則沿用上次 cohort 前推;偵測跌穿。"""
    latest = store.latest(conn)
    today_date = max(price_by_date)
    if fresh_cohort:
        row = {**fresh_cohort, "date": today_date, "price": price}
        row.setdefault("cohort_date", today_date)
    elif latest:
        row = {k: latest[k] for k in
               ("lth_btc", "sth_btc", "circulating_btc", "sth_cost_basis", "lth_cost_basis")}
        row["date"] = today_date
        row["price"] = price
        row["cohort_date"] = latest.get("cohort_date") or latest["date"]  # 保留 cohort 真正日期
    else:
        raise SystemExit("尚無 cohort 資料,且即時來源抓取失敗。")
    prev = latest or row
    store.upsert_cohort(conn, row)
    sigs = judge.detect(row, prev, store.recent(conn, 90))
    if notifier and any(s.level == "alert" for s in sigs):
        notifier.send(sigs)
    export.write_data_js(
        export.build_dashboard_data(price_by_date, store.recent(conn, 400), store.latest(conn)),
        data_js_path)
    return sigs


def make_notifier(env=os.environ):
    """依環境變數選推播通道:LINE 優先,否則 Telegram,都沒設就不推(網站照常更新)。
    兩個變數都要有才算數——只設一半視為沒設,不要在半夜炸 KeyError。"""
    from holder_radar.notify import LineAdapter, TelegramAdapter
    if env.get("LINE_TOKEN") and env.get("LINE_TO"):
        return LineAdapter(env["LINE_TOKEN"], env["LINE_TO"])
    if env.get("TG_TOKEN") and env.get("TG_CHAT_ID"):
        return TelegramAdapter(env["TG_TOKEN"], env["TG_CHAT_ID"])
    return None


def snapshot(conn, cohort_source, as_of_date: str, price: float) -> dict:
    """BigQuery 全量更新 cohort（吃 ~0.45TB 額度，≤2次/月）。"""
    row = {**cohort_source.run(), "date": as_of_date, "price": price, "cohort_date": as_of_date}
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
    elif cmd == "test-push":
        # 手動發一則測試警報:驗憑證 / 拍片用。
        # 訊息文案沿用 judge.detect(單一來源),成本線取 DB 最新真實值;只假造價格跨線讓警報觸發。
        notifier = make_notifier()
        if not notifier:
            raise SystemExit(
                "沒有可用的推播通道。擇一設定:\n"
                "  LINE:     LINE_TOKEN + LINE_TO\n"
                "  Telegram: TG_TOKEN + TG_CHAT_ID")
        latest = store.latest(conn)
        if not latest:
            raise SystemExit("DB 尚無 cohort 資料,先跑一次 daily。")
        c = latest["sth_cost_basis"]
        sigs = judge.detect({**latest, "price": c - 1}, {**latest, "price": c + 1}, [])
        notifier.send(sigs)
        print(f"已送出測試警報(成本線 ${c:,.0f}),看你的 {notifier.name}。")
    else:  # daily
        from holder_radar import bgeometrics
        px = prices.daily_history(180)
        try:
            fresh = bgeometrics.fetch_cohort()      # 免費即時 cohort
        except Exception as e:
            print(f"bgeometrics 抓取失敗,改用上次 cohort 前推:{e}")
            fresh = None
        daily(conn, make_notifier(), prices.current_btc_usd(), px,
              "app/assets/data.js", fresh_cohort=fresh)


if __name__ == "__main__":  # 少了這行,`python -m holder_radar.cli` 會靜默 no-op(exit 0)
    main()
