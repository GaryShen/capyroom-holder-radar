"""LINE 查詢:使用者先問、bot 才答 → 走免費無限的 Reply API。"""
from holder_radar import judge
from holder_radar.judge import DISCLAIMER


def handle_query(latest: dict) -> str:
    """純函式:把最新 cohort 變成一句繁中現況 + 免責。webhook 拿去 reply。"""
    if not latest:
        return f"目前還沒有資料,稍候再查。\n{DISCLAIMER}"
    return f"{judge.summarize_zh(latest)}\n{DISCLAIMER}"
