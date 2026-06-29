"""CoinGecko 免費價格。"""
import requests
from datetime import datetime, timezone

BASE = "https://api.coingecko.com/api/v3"


def current_btc_usd(get=requests.get) -> float:
    r = get(f"{BASE}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"}, timeout=20)
    r.raise_for_status()
    return float(r.json()["bitcoin"]["usd"])


def daily_history(days: int, get=requests.get) -> dict[str, float]:
    r = get(f"{BASE}/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"}, timeout=30)
    r.raise_for_status()
    out: dict[str, float] = {}
    for ms, usd in r.json()["prices"]:
        d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        out[d] = float(usd)
    return out
