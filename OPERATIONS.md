# 운영 및 다른 PC 인계

GitHub에는 프로그램과 운영 규칙만 저장한다. Telegram 토큰, 구독자 Chat ID, CGV 로그인, 저장 카드 정보는 절대 저장하지 않는다.

## 새 PC에서 복구

1. 이 저장소를 clone한다.
2. `.env.example`을 `.env`로 복사하고 새 PC에서 Telegram 토큰을 입력한다.
3. 기존 봇 대화에서 구독자들이 `/start`를 다시 보내게 한다. Chat ID는 새 PC의 `data/subscribers.json`에 생성된다.
4. `python3 -m unittest -v test_monitor_core.py`를 실행한다.
5. macOS라면 `sh install_macos_service.sh`를 실행한다.
6. CGV 내부 브라우저를 열고 소유자가 로그인한다.
7. `watch-config.example.json`을 기준으로 30분 감시를 만든다.

## 장애 시 동작

- Telegram 구독 명령 서비스는 로그인 시 자동 시작되고 비정상 종료 시 재시작한다.
- CGV 로그아웃 상태에서도 공개 상영표와 가능한 좌석 조회를 계속한다.
- 조건 좌석을 발견했는데 로그아웃이면 Telegram으로 로그인을 요청하고 추적은 중단하지 않는다.
- CGV 또는 내부 브라우저 자체가 접근 불가하면 실패 사실을 Telegram으로 알리고 다음 주기에 재시도한다.

## 다중 PC 주의사항

GitHub clone만으로 CGV 로그인 세션이나 Codex 예약 작업이 다른 PC에 실시간 승계되지는 않는다. 끊김 없는 장애 조치를 위해서는 두 번째 PC에도 위 복구 절차와 별도의 예약 작업이 미리 준비되어 있어야 한다. 같은 Telegram Bot API의 `getUpdates`를 두 PC에서 동시에 소비하면 명령이 나뉠 수 있으므로 구독 명령 서비스는 한 PC에서만 활성화한다. 좌석 감시는 중복 실행할 수 있지만 Telegram 중복 알림 방지 상태를 공유하지 않으면 같은 결과가 두 번 갈 수 있다.
