"""判讀層:純函式,零 I/O。把 cohort 數字變成繁中訊號。"""
from dataclasses import dataclass

DISCLAIMER = "—— 本內容僅為資料整理,非投資建議。"


@dataclass
class Signal:
    kind: str   # sth_cross_down / sth_cross_up / lth_supply_high / sth_supply_low / none
    level: str  # alert / info
    zh: str


def detect(today: dict, prev: dict, history: list[dict]) -> list[Signal]:
    sigs: list[Signal] = []
    c = today["sth_cost_basis"]
    if prev["price"] >= prev["sth_cost_basis"] and today["price"] < c:
        sigs.append(Signal("sth_cross_down", "alert",
            f"⚠️ 比特幣跌穿短期持有者成本線(約 ${c:,.0f})——最近約半年買進的人,平均帳面套牢。"))
    if prev["price"] < prev["sth_cost_basis"] and today["price"] >= c:
        sigs.append(Signal("sth_cross_up", "alert",
            f"📈 比特幣站回短期持有者成本線(約 ${c:,.0f})——最近半年買家平均回到帳面解套。"))
    if history:
        if today["lth_btc"] > max(h["lth_btc"] for h in history):
            sigs.append(Signal("lth_supply_high", "info",
                "📊 長期持有者供給創區間新高——市場上願意賣的幣被抽乾(浮動籌碼枯竭)。"))
        if today["sth_btc"] < min(h["sth_btc"] for h in history):
            sigs.append(Signal("sth_supply_low", "info",
                "🧊 短期持有者供給跌到區間新低——新進場的幣幾乎被洗空。"))
    if not sigs:
        sigs.append(Signal("none", "info", summarize_zh(today)))
    return sigs


def summarize_zh(today: dict) -> str:
    circ = today["circulating_btc"]
    lth_pct = 100 * today["lth_btc"] / circ if circ else 0
    under = today["price"] < today["sth_cost_basis"]
    state = "新手平均套牢、老手抱緊" if under else "新手平均帳面獲利"
    return (f"長期持有者握約 {lth_pct:.0f}% 供給;"
            f"現價 ${today['price']:,.0f} vs 短期持有者成本線 ${today['sth_cost_basis']:,.0f}——{state}。")
