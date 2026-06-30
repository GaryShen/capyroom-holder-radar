"""把資料變成儀表板吃的 window.RADAR_DATA。

接點:輸出 app/assets/data.js(同步 <script>,免 fetch、file:// 與 Pages 都能跑)。
- price:近 N 天日線(CoinGecko 免費,天天可更新)
- cost / lth:STH 成本線、LTH 供給%——慢變數,來自 ≤2次/月的 BigQuery 快照;
  歷史點不足時用「最新已知值」補平,隨快照累積逐步填實。
"""
import json
from holder_radar import judge

N = 180


def _series_from_snapshots(price_dates, snapshots, key):
    """把稀疏快照(date→值)對齊到 price_dates;缺的用最近一筆已知值補(forward-fill)。"""
    by_date = {s["date"]: s[key] for s in snapshots if s.get(key) is not None}
    out, last = [], None
    for d in price_dates:
        if d in by_date:
            last = by_date[d]
        out.append(last)
    # 開頭若還沒有任何快照,用第一個已知值回填
    first = next((v for v in out if v is not None), None)
    return [v if v is not None else first for v in out]


def build_dashboard_data(price_by_date: dict, snapshots: list[dict], latest: dict) -> dict:
    """price_by_date: {date: usd};snapshots: store.recent();latest: store.latest()。"""
    dates = sorted(price_by_date)[-N:]
    price = [price_by_date[d] for d in dates]
    cost = _series_from_snapshots(dates, snapshots, "sth_cost_basis")
    lth_pct = _series_from_snapshots(
        dates, [{"date": s["date"],
                 "v": 100 * s["lth_btc"] / s["circulating_btc"] if s["circulating_btc"] else None}
                for s in snapshots], "v")
    lp = 100 * latest["lth_btc"] / latest["circulating_btc"] if latest["circulating_btc"] else 0
    cb = latest["sth_cost_basis"]
    cur_price = price[-1] if price else latest["price"]   # 現價一律取最新價格點,與圖表同步
    latest = {**latest, "price": cur_price}
    under = cur_price < cb
    under_pct = (cb - cur_price) / cb * 100 if cb else 0
    return {
        "meta": {"as_of": latest["date"], "source": "BigQuery 公開資料集 × CoinGecko",
                 "price_as_of": dates[-1] if dates else latest["date"],          # 價格即時
                 "cohort_as_of": latest.get("cohort_date") or latest["date"],    # 持有者結構算出日(凍結)
                 "disclaimer": "本內容僅為資料整理,非投資建議。"},
        "price": price, "cost": cost, "lth": lth_pct,
        "donut": {"lth_pct": round(lp / 100, 4),
                  "lth_btc": latest["lth_btc"], "sth_btc": latest["sth_btc"]},
        "latest": {"price": latest["price"], "sth_cost_basis": cb,
                   "lth_pct": round(lp, 1), "underwater": under,
                   # 給儀表板直接塞的顯示字串
                   "headline": judge.summarize_zh(latest),
                   "price_str": f"${latest['price']:,.0f}",
                   "cost_str": f"${cb:,.0f}",
                   "lth_pct_str": f"{lp:.0f}%",
                   "lth_btc_str": f"{latest['lth_btc'] / 1e6:.2f}M",
                   "sth_btc_str": f"{latest['sth_btc'] / 1e6:.2f}M",
                   "underwater_str": f"{under_pct:.1f}%"},
    }


def write_data_js(data: dict, path: str) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"window.RADAR_DATA = {payload};\n")
