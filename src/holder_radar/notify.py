"""通知層:judge 邏輯與「推到哪」解耦。換通道只是換 adapter。"""
import requests
from holder_radar.judge import DISCLAIMER


def format_message(signals) -> str:
    body = "\n".join(s.zh for s in signals)
    return f"{body}\n{DISCLAIMER}"


class LineAdapter:
    name = "LINE"

    def __init__(self, token, to, post=requests.post):
        self.token, self.to, self.post = token, to, post

    def send(self, signals) -> None:
        r = self.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"to": self.to, "messages": [{"type": "text", "text": format_message(signals)}]},
            timeout=20)
        r.raise_for_status()


class TelegramAdapter:
    name = "Telegram"

    def __init__(self, token, chat_id, post=requests.post):
        self.token, self.chat_id, self.post = token, chat_id, post

    def send(self, signals) -> None:
        r = self.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": self.chat_id, "text": format_message(signals)},
            timeout=20)
        r.raise_for_status()
