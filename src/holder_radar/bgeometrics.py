"""免費 cohort 來源:api.bgeometrics.com(BGeometrics)REST,無需 API key。

取代 BigQuery —— LTH/STH 供給與成本線天天免費保鮮、你帳號零費用。
免費層 10 次/小時(全域);每日只需 4 次呼叫,遠遠夠用。

端點(HATEOAS):GET /{endpoint}?sort=unixTs,desc&size=1 → 最新一筆。
回應:{"_embedded": {endpoint: [{"unixTs":..., "<value>":..., "_links":{self:{href:.../YYYY-MM-DD}}}]}}
"""
import requests

BASE = "https://api.bgeometrics.com"

# 我們的 cohort 欄位 → BGeometrics 端點
METRICS = {
    "sth_cost_basis": "sthRealizedPrices",
    "lth_cost_basis": "lthRealizedPrices",
    "lth_btc": "longTermHodlerSupplyBtcs",
    "sth_btc": "shortTermHodlerSupplyBtcs",
}


def _pick_value(item: dict) -> float:
    """從一筆抓數值:跳過時間戳與 _links,取第一個能轉 float 的欄位。"""
    for k, v in item.items():
        if k in ("unixTs", "_links"):
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    raise ValueError(f"找不到數值欄位:{item}")


def _latest(endpoint: str, get=requests.get) -> tuple[float, str]:
    r = get(f"{BASE}/{endpoint}", params={"sort": "unixTs,desc", "size": 1}, timeout=20)
    r.raise_for_status()
    item = r.json()["_embedded"][endpoint][0]
    date = item.get("_links", {}).get("self", {}).get("href", "").rsplit("/", 1)[-1]
    return _pick_value(item), date


def fetch_cohort(get=requests.get) -> dict:
    """回傳與 BigQuery 同格式的 cohort dict(+ cohort_date)。免費、即時。"""
    out: dict = {}
    date = None
    for key, endpoint in METRICS.items():
        out[key], date = _latest(endpoint, get)
    out["circulating_btc"] = out["lth_btc"] + out["sth_btc"]
    out["cohort_date"] = date
    return out
