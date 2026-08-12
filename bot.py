"""CGV 천호/용산 IMAX 좌석 오픈 알리미.

CGV 페이지 구조가 변경될 수 있어 조회부는 별도 어댑터로 분리했다.
운영 전에는 CGV 응답에서 실제 timetable/seat API를 확인해 CgvProvider를
구체화해야 한다. Telegram 제어부와 상태 비교 로직은 독립적으로 동작한다.
"""
from __future__ import annotations
import json, os, re, time, subprocess
from dataclasses import dataclass, asdict
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Dict, List
import requests
from dotenv import load_dotenv
from monitor_core import SubscriberStore

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "state.json"
SUBSCRIBERS = ROOT / "data" / "subscribers.json"
load_dotenv(ROOT / ".env")

@dataclass(frozen=True)
class Screening:
    theater: str
    movie: str
    ymd: str
    time: str
    url: str
    seats: int = -1

class CgvProvider:
    """브라우저에서 CGV 내부 timetable 응답을 가로채는 조회 어댑터."""
    theaters = {"용산": "0013", "천호": "0198"}
    def fetch(self, ymd: str) -> List[Screening]:
        p = subprocess.run(["node", str(ROOT/"cgv_browser.js"), ymd], capture_output=True, text=True, timeout=60)
        if p.returncode: raise RuntimeError(p.stderr[-500:] or "browser fetch failed")
        rows=json.loads(p.stdout.strip().splitlines()[-1])
        return [Screening(**x) for x in rows]

class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.offset = 0
    def call(self, method: str, **params):
        r = requests.post(f"{self.base}/{method}", data=params, timeout=30)
        r.raise_for_status(); body = r.json()
        if not body.get("ok"): raise RuntimeError(body)
        return body["result"]
    def send(self, chat_id: str, text: str):
        return self.call("sendMessage", chat_id=chat_id, text=text, disable_web_page_preview="true")
    def updates(self):
        rows = self.call("getUpdates", offset=self.offset, timeout=25, allowed_updates='["message"]')
        for row in rows:
            self.offset = row["update_id"] + 1
            yield row

def load_state() -> Dict:
    if STATE.exists(): return json.loads(STATE.read_text())
    return {"watching": True, "days": 7, "interval": int(os.getenv("POLL_INTERVAL_SEC", "20")), "seen": {}}
def save_state(s):
    STATE.parent.mkdir(exist_ok=True); STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2))

WEEKDAYS = ['월','화','수','목','금','토','일']
def format_item(item: Screening) -> str:
    d = datetime.strptime(item.ymd, '%Y%m%d')
    seats = '조회불가' if item.seats < 0 else f'{item.seats}석'
    return (f'📅 관람 일시: {d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]}요일) {item.time}\n'
            f'🎬 영화: {item.movie}\n🏢 극장: CGV {item.theater} IMAX\n'
            f'💺 현재 잔여 좌석: {seats}\n🔗 예매 페이지: {item.url}')

def help_text():
    return "🎟️ 좌석 레이더 이용 방법이에요.\n\n" \
           "/start - 명당 알림을 시작해요.\n" \
           "/stop - 알림을 잠시 쉬어요.\n" \
           "/status - 레이더 상태를 확인해요.\n" \
           "/report - 지금 열린 회차를 살펴봐요.\n" \
           "/days N - 확인할 날짜 범위를 정해요.\n\n" \
           "좋은 좌석은 예고 없이 나타나지만 걱정 마세요. 제가 계속 살펴볼게요! 🍿"

def target_dates(days: int):
    """오늘을 제외하고 앞으로의 금·토·일만 반환한다."""
    result=[]
    for i in range(1, days + 1):
        d=date.today()+timedelta(days=i)
        if d.weekday() in (4,5,6): result.append(d.strftime('%Y%m%d'))
    return result

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: raise SystemExit("TELEGRAM_BOT_TOKEN is missing; copy .env.example to .env")
    tg, provider, state = Telegram(token), CgvProvider(), load_state()
    subscribers = SubscriberStore(SUBSCRIBERS, os.getenv("TELEGRAM_CHAT_ID"))
    subscribers.save(subscribers.load())

    def broadcast(text: str):
        for subscriber_id in subscribers.load():
            try:
                tg.send(subscriber_id, text)
            except Exception as e:
                print(f'broadcast warning {subscriber_id}: {e}')
    print("bot started")
    while True:
        try:
            for u in tg.updates():
                msg = u.get("message", {}); chat = msg.get("chat", {}); text = (msg.get("text") or "").strip()
                cid = str(chat.get("id", ""))
                if text == "/start":
                    subscribers.add(cid)
                    state["watching"] = True
                    tg.send(cid, "🎬 좌석 레이더를 켰어요!\n\n용산·천호 IMAX에 좋은 자리가 나타나면 바로 알려드릴게요. 지금 열린 회차도 함께 살펴보는 중이에요. 잠시만 기다려주세요 🍿")
                    try:
                        latest=[]
                        for ymd in target_dates(state['days']):
                            try: latest.extend(provider.fetch(ymd))
                            except Exception as e: print(f'start report warning {ymd}: {e}')
                        latest = sorted(latest, key=lambda x: (x.ymd, x.time), reverse=True)
                        if latest:
                            tg.send(cid, '앞으로 다가오는 금·토·일 IMAX 회차 중 현재 확인되는 최신 회차를 안내해 드립니다.\n\n' + '\n\n'.join(format_item(x) for x in latest[:10]))
                        else:
                            tg.send(cid, '앞으로 다가오는 금·토·일에 현재 확인되는 천호·용산 IMAX 상영 회차가 없습니다. 새로운 회차가 열리면 감시 알림으로 바로 알려드리겠습니다.')
                    except Exception:
                        tg.send(cid, '현재 최신 회차 조회가 지연되고 있습니다. 감시는 정상적으로 시작했으며, 조회가 가능한 순간 좌석 변동을 알려드리겠습니다.')
                elif text == "/stop":
                    subscribers.remove(cid)
                    tg.send(cid, "🔕 좌석 레이더를 잠시 껐어요. 다시 명당 탐색을 시작하려면 /start 를 보내주세요!")
                elif text == "/status": tg.send(cid, f"현재 감시 상태를 안내해 드립니다.\n\n감시 상태: {'정상적으로 감시 중입니다.' if state['watching'] else '현재 중지되어 있습니다.'}\n확인 주기: 약 {state['interval']}초마다\n확인 범위: 오늘 이후 {state['days']}일 안의 금·토·일\n대상 극장: CGV 천호 IMAX, CGV 용산아이파크몰 IMAX")
                elif text == "/report":
                    tg.send(cid, '현재 CGV 천호·용산 IMAX 상영표를 확인하고 있습니다.\n잠시만 기다려 주세요. 확인이 끝나는 대로 날짜·요일·시간·극장·영화·잔여 좌석을 자세히 보내드리겠습니다.')
                    rows=[]
                    # 수동 보고는 즉시성을 우선해 오늘 회차를 먼저 보고한다.
                    for ymd in target_dates(state['days']):
                        try: rows.extend(provider.fetch(ymd))
                        except Exception as e: print(f'report warning {ymd}: {e}')
                    if rows:
                        for start in range(0,len(rows),8): tg.send(cid, '현재 CGV IMAX 회차\n\n'+'\n\n'.join(format_item(x) for x in rows[start:start+8]))
                    else: tg.send(cid, '현재 확인된 CGV 천호·용산 IMAX 상영 회차가 없습니다.\n\n아직 해당 날짜의 상영 일정이 열리지 않았거나 CGV 응답이 잠시 지연되고 있을 수 있습니다. 감시를 켜두시면 새로운 회차가 확인되는 즉시 알려드리겠습니다.')
                elif text == "/help": tg.send(cid, help_text())
                elif text.startswith("/days "):
                    state["days"] = max(1, min(14, int(text.split()[1]))); tg.send(cid, f"감시 범위: {state['days']}일")
                save_state(state)
            if state["watching"]:
                for ymd in target_dates(state["days"]):
                    for item in provider.fetch(ymd):
                        key = "|".join([item.theater, item.movie, item.ymd, item.time])
                        if state["seen"].get(key) != item.seats:
                            state["seen"][key] = item.seats
                            broadcast('🔔 CGV IMAX 좌석 변동을 확인했습니다.\n\n'+format_item(item)+'\n\n지금 예매 페이지에서 좌석 상태를 한 번 더 확인해 주세요.')
                save_state(state)
        except Exception as e:
            print(f"warning: {e}")
        time.sleep(state["interval"])

if __name__ == "__main__": main()
