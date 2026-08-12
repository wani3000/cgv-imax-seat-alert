"""Lightweight Telegram subscription service.

This process never calls CGV and never uses an LLM. It only consumes Telegram
commands and maintains data/subscribers.json.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from requests import HTTPError

from monitor_core import SubscriberStore


ROOT = Path(__file__).resolve().parent
OFFSET_FILE = ROOT / "data" / "telegram-offset.json"


def load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env(ROOT / ".env")


def load_offset() -> int:
    if not OFFSET_FILE.exists():
        return 0
    return int(json.loads(OFFSET_FILE.read_text(encoding="utf-8")).get("offset", 0))


def save_offset(offset: int) -> None:
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing")
    base = f"https://api.telegram.org/bot{token}"
    store = SubscriberStore(
        ROOT / "data" / "subscribers.json", os.getenv("TELEGRAM_CHAT_ID")
    )
    store.save(store.load())
    offset = load_offset()

    def send(chat_id: str, text: str) -> None:
        response = requests.post(
            f"{base}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=20,
        )
        response.raise_for_status()

    while True:
        try:
            response = requests.get(
                f"{base}/getUpdates",
                params={"offset": offset, "timeout": 25, "allowed_updates": '["message"]'},
                timeout=35,
            )
            response.raise_for_status()
            for update in response.json().get("result", []):
                offset = int(update["update_id"]) + 1
                save_offset(offset)
                message = update.get("message") or {}
                chat_id = str((message.get("chat") or {}).get("id", ""))
                text = (message.get("text") or "").strip().split()[0]
                if not chat_id:
                    continue
                if text == "/start":
                    store.add(chat_id)
                    send(chat_id, "🎬 좌석 레이더를 켰어요!\n\n용산·천호 IMAX 명당에 빈자리가 반짝 나타나면 빠르게 알려드릴게요. 영화 고를 준비만 해두세요 🍿\n\n알림을 쉬고 싶을 때는 /stop 을 보내주세요.")
                elif text == "/stop":
                    store.remove(chat_id)
                    send(chat_id, "🔕 좌석 레이더를 잠시 껐어요.\n\n다시 명당 탐색을 시작하고 싶을 때 /start 를 보내주세요. 언제든 다시 출동할게요!")
                elif text == "/status":
                    subscribed = chat_id in store.load()
                    send(chat_id, "🟢 지금 열심히 명당을 살펴보고 있어요. 좋은 좌석이 보이면 바로 소식 전할게요!" if subscribed else "⚪ 지금은 좌석 레이더가 쉬는 중이에요. /start 를 보내면 다시 살펴볼게요!")
                elif text == "/help":
                    send(chat_id, "🎟️ 이용 방법을 알려드릴게요.\n\n/start  명당 알림 시작하기\n/stop  알림 잠시 쉬기\n/status  좌석 레이더 상태 보기\n\n좋은 자리는 예고 없이 등장해요. 레이더는 제가 지켜볼게요!")
        except HTTPError as exc:
            # requests' default exception string includes the full request URL,
            # which contains the Telegram bot token. Log only safe metadata.
            status = exc.response.status_code if exc.response is not None else "unknown"
            endpoint = "getUpdates" if exc.request and exc.request.method == "GET" else "sendMessage"
            print(f"subscription warning: Telegram HTTP {status} at {endpoint}", flush=True)
            time.sleep(5)
        except Exception as exc:
            print(f"subscription warning: {type(exc).__name__}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
