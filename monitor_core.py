"""Token-free monitoring primitives for the CGV seat watcher.

This module intentionally contains no browser or LLM integration.  A provider
supplies normalized screenings/seats; this module calculates dates, detects
changes, persists state, and sends Telegram notifications.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, order=True)
class WatchDate:
    ymd: str
    start_hour: int = 0


@dataclass(frozen=True, order=True)
class SeatResult:
    theater: str
    ymd: str
    time: str
    seats: tuple[str, ...]

    @property
    def key(self) -> str:
        return "|".join((self.theater, self.ymd, self.time))


def upcoming_watch_dates(today: date, weekend_count: int = 3,
                         extra_dates: Iterable[date] = ()) -> list[WatchDate]:
    """Return the next weekend plus following weekends and future exceptions."""
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.weekday() == 4:
        days_until_friday = 7
    first_friday = today + timedelta(days=days_until_friday)
    result: set[WatchDate] = set()
    for week in range(weekend_count):
        friday = first_friday + timedelta(days=7 * week)
        result.add(WatchDate(friday.strftime("%Y%m%d"), 19))
        result.add(WatchDate((friday + timedelta(days=1)).strftime("%Y%m%d")))
        result.add(WatchDate((friday + timedelta(days=2)).strftime("%Y%m%d")))
    for extra in extra_dates:
        if extra > today:
            result.add(WatchDate(extra.strftime("%Y%m%d")))
    return sorted(result)


def adjacent_target_pairs(seats: Iterable[str], rows: str = "GHIJ") -> list[str]:
    """Find adjacent pairs in target rows from normalized seat names."""
    grouped: dict[str, set[int]] = {row: set() for row in rows}
    for seat in seats:
        if len(seat) < 2 or seat[0] not in grouped or not seat[1:].isdigit():
            continue
        grouped[seat[0]].add(int(seat[1:]))
    pairs: list[str] = []
    for row, numbers in grouped.items():
        for number in sorted(numbers):
            if number + 1 in numbers:
                pairs.append(f"{row}{number}·{row}{number + 1}")
    return pairs


class SnapshotStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, list[str]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def compare_and_save(self, results: Iterable[SeatResult]) -> dict[str, dict]:
        before = self.load()
        after = {item.key: list(item.seats) for item in results}
        changes: dict[str, dict] = {}
        for key in sorted(set(before) | set(after)):
            old, new = before.get(key), after.get(key)
            if old != new:
                changes[key] = {"before": old, "after": new}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")
        return changes


class SubscriberStore:
    def __init__(self, path: Path, initial_chat_id: str | None = None):
        self.path = path
        self.initial_chat_id = initial_chat_id

    def load(self) -> set[str]:
        subscribers: set[str] = set()
        if self.path.exists():
            subscribers.update(str(x) for x in json.loads(
                self.path.read_text(encoding="utf-8")
            ))
        elif self.initial_chat_id:
            subscribers.add(str(self.initial_chat_id))
        return subscribers

    def save(self, subscribers: Iterable[str]) -> None:
        normalized = sorted({str(x) for x in subscribers if str(x)})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(self, chat_id: str) -> bool:
        subscribers = self.load()
        before = len(subscribers)
        subscribers.add(str(chat_id))
        self.save(subscribers)
        return len(subscribers) != before

    def remove(self, chat_id: str) -> bool:
        subscribers = self.load()
        existed = str(chat_id) in subscribers
        subscribers.discard(str(chat_id))
        self.save(subscribers)
        return existed


def send_telegram(text: str, token: str | None = None,
                  chat_id: str | None = None) -> int:
    token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.load(response)
    if not body.get("ok"):
        raise RuntimeError("Telegram sendMessage failed")
    return int(body["result"]["message_id"])


def broadcast_telegram(text: str, chat_ids: Iterable[str],
                       token: str | None = None) -> dict[str, str | int]:
    """Send independently so one blocked chat does not stop the broadcast."""
    results: dict[str, str | int] = {}
    for chat_id in sorted({str(x) for x in chat_ids if str(x)}):
        try:
            results[chat_id] = send_telegram(text, token=token, chat_id=chat_id)
        except Exception as exc:
            results[chat_id] = f"error: {type(exc).__name__}"
    return results
