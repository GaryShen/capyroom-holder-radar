"""免費 cohort 來源:bitcoin-data.com(BGeometrics)REST API,無需 API key。

取代 BigQuery —— LTH/STH 供給與成本線天天免費保鮮、你帳號零費用。
免費層 10 次/小時;每日只需 4 次呼叫(4 個指標各一次),遠遠夠用。

端點格式:GET https://bitcoin-data.com/v1/{metric}/last → 最新一筆 JSON。
回應欄位名待用真實樣本確認(_pick_value 防禦式自動抓數值欄位,容錯)。
"""
import requests

BASE = "https://bitcoin-data.com/v1"

# 各 cohort 指標 → bitcoin-data.com 端點(kebab-case)
METRICS = {
    "sth_cost_basis": "sth-realized-price",
    "lth_cost_basis": "lth-realized-price",
    "lth_btc": "long-term-holder-supply",
    "sth_btc": "short-term-holder-supply",
}

# 日期/時間戳欄位(略過,不當數值)
_DATE_KEYS = {"d", "theday", "theDate", "date", "day", "unixts", "unixTs", "timestamp", "t"}


def _pick_value(obj: dict) -> float:
    """從一筆回應抓出指標數值:跳過日期/時間戳,取第一個能轉 float 的欄位。"""
    if isinstance(obj, list):
        obj = obj[-1]
    for k, v in obj.items():
        if k in _DATE_KEYS or k.lower() in {x.lower() for x in _DATE_KEYS}:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    raise ValueError(f"找不到數值欄位:{obj}")


def _latest(metric_path: str, get=requests.get) -> float:
    r = get(f"{BASE}/{metric_path}/last", timeout=20)
    r.raise_for_status()
    return _pick_value(r.json())


def fetch_cohort(get=requests.get) -> dict:
    """回傳與 BigQuery 同格式的 cohort dict(免費、即時)。"""
    vals = {key: _latest(path, get) for key, path in METRICS.items()}
    vals["circulating_btc"] = vals["lth_btc"] + vals["sth_btc"]
    return vals
