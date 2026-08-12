# CGV 천호·용산 IMAX 좌석 오픈 알리미

## 인계 문서

이 저장소는 CGV 천호(`0199`)와 용산아이파크몰(`0013`) IMAX의 미래 금·토·일 상영 회차와 잔여 좌석을 조회해 Telegram으로 알리는 작업용 프로젝트입니다.

### 현재까지 한 일

- Telegram 봇 `@cgvmaxlovebot` 연결
- `/start`, `/stop`, `/status`, `/report`, `/days N`, `/help` 명령 구현
- 날짜·요일·시간·영화·극장·잔여 좌석을 친절한 존댓말로 보고
- 오늘 날짜를 제외하고 미래 금·토·일만 감시하도록 구현
- 새 회차·좌석 수 변화 비교 및 중복 알림 방지 상태 저장
- Puppeteer 기반 CGV 동적 페이지 조회 시도
- Chrome/내부 브라우저에서 CGV 상영표와 IMAX DOM 구조 확인
- 30분 주기 Codex heartbeat 감시 `cgv-imax-30` 등록

### 현재 확인된 제한

로컬 Puppeteer 실행 환경은 CGV에서 비정상 접속으로 차단되지만, Codex 내부 브라우저에서는 상영표가 정상적으로 표시됩니다. 따라서 `cgv_browser.js`는 일반적인 자동 브라우저 실행 방식이고, 안정적인 운영을 위해서는 CGV에 정상 접근되는 브라우저 세션 또는 별도 실행 환경으로 조회부를 옮겨야 합니다.

CGV 로그인 및 예매 자동화는 구현하지 않았습니다. 비밀번호·세션·결제 정보는 저장소에 절대 넣지 않습니다. 조건에 맞는 좌석을 찾더라도 최종 결제·예매 확정은 사용자 확인을 거쳐야 합니다.

### 다음 작업

1. 정상 접근되는 Chrome 세션에서 CGV 상영표/좌석 조회를 수행하는 브리지 구성
2. IMAX·오디세이·G~J열·중앙 기준 좌우 15칸·연석 2좌석 필터 추가
3. 조건 일치 시 Telegram에 날짜·시간·극장·좌석명을 먼저 보고
4. 사용자가 확인한 뒤에만 예매 페이지의 좌석 선택 단계까지 진행
5. CGV 화면 변경과 차단 상태를 감지하는 QA 테스트 추가

### 실행

## 실행

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

`.env`에 Telegram Bot Token과 알림 Chat ID를 넣는다. 토큰은 소스나 Git에 저장하지 않는다.

현재 Telegram 제어부, 폴링, 상태 저장, 중복 알림 방지는 준비되어 있다. CGV가 비로그인 웹 요청을 차단할 수 있어 실제 운영 전 `CgvProvider.fetch()`를 CGV의 현재 timetable/seat 응답에 맞춰 연결해야 한다.

### 토큰을 사용하지 않는 로컬 감시 코어

`monitor_core.py`는 브라우저나 LLM과 분리된 순수 Python 모듈이다.

- 실행일 기준 가장 가까운 주말부터 3개 주말의 금·토·일을 계산
- 금요일은 19시 이후, 토·일은 전 시간대로 정규화
- 2026-08-17 같은 일회성 예외 날짜 지원
- G~J열 연석 탐지
- 직전 스냅샷과 신규 일정·좌석 변화를 비교하고 JSON으로 저장
- Telegram Bot API 직접 전송

이 모듈은 반복 실행해도 모델 토큰을 사용하지 않는다. 현재 남은 연결 지점은 CGV가 허용하는 로그인 브라우저 세션에서 정규화된 회차·좌석 데이터를 공급하는 provider bridge다. 로컬 CGV 요청은 403으로 차단될 수 있으므로 브리지가 완성되기 전에는 기존 Codex 내부 브라우저 감시를 유지한다.

```bash
python3 -m unittest -v test_monitor_core.py
```

### Telegram 다중 사용자 구독

`subscription_bot.py`는 CGV를 조회하지 않는 경량 명령 처리 프로세스다.

- `/start`: 현재 Chat ID를 `data/subscribers.json`에 등록
- `/stop`: 현재 Chat ID 구독 해제
- `/status`: 본인의 구독 상태 확인
- `/help`: 명령 안내

감시 결과는 `monitor_core.broadcast_telegram()`을 통해 모든 구독자에게 독립적으로 전송한다. 한 사용자가 봇을 차단했거나 전송에 실패해도 나머지 구독자 알림은 계속된다.

```bash
python3 subscription_bot.py
```

다른 PC 인계와 macOS 자동 실행 방법은 `OPERATIONS.md`를 참고한다. 감시 조건의 이식 가능한 기준은 `watch-config.example.json`, 에이전트 행동 규칙은 `AGENTS.md`에 정리되어 있다.
