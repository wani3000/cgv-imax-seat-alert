# 운영 및 다른 PC 인계

GitHub에는 프로그램과 운영 규칙만 저장한다. Telegram 토큰, 구독자 Chat ID, CGV 로그인, 저장 카드 정보는 절대 저장하지 않는다.

## 새 PC에서 복구

1. 이 저장소를 clone한다.
2. `.env.example`을 `.env`로 복사하고 새 PC에서 Telegram 토큰을 입력한다. 새 PC의 `TELEGRAM_INSTANCE_ROLE`은 `standby`로 유지한다.
3. `./setup_payment_keychain.sh`를 실행해 이 Mac의 로그인 키체인에 Toss 식별 정보를 등록한다. 실제 값은 GitHub로 복사하지 않는다.
4. 기존 봇 대화에서 구독자들이 `/start`를 다시 보내게 한다. Chat ID는 새 PC의 `data/subscribers.json`에 생성된다.
5. `python3 -m unittest -v test_monitor_core.py`를 실행한다.
6. macOS라면 `sh install_macos_service.sh`를 실행한다.
7. CGV 내부 브라우저를 열고 소유자가 로그인한다.
8. `watch-config.example.json`을 기준으로 30분 감시를 만든다.

결제 준비의 상세 순서와 최종 확인 경계는 `PAYMENT_AUTOMATION.md`를 따른다.

## 장애 시 동작

- Telegram 구독 명령 서비스는 로그인 시 자동 시작되고 비정상 종료 시 재시작한다.
- CGV 로그아웃 상태에서도 공개 상영표와 가능한 좌석 조회를 계속한다.
- 조건 좌석을 발견했는데 로그아웃이면 Telegram으로 로그인을 요청하고 추적은 중단하지 않는다.
- CGV 또는 내부 브라우저 자체가 접근 불가하면 실패 사실을 Telegram으로 알리고 다음 주기에 재시도한다.

## 다중 PC 주의사항

GitHub clone만으로 CGV 로그인 세션이나 Codex 예약 작업이 다른 PC에 실시간 승계되지는 않는다. 역할 지정과 안전한 전환 절차는 `MULTI_PC_FAILOVER.md`를 반드시 따른다.
