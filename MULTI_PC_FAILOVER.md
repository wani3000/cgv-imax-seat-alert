# 다중 PC 안전 운영 규칙

## 반드시 지킬 구조

- **주 PC (`primary`) 한 대만** Telegram의 `/start`, `/stop`, `/status`, `/help` 명령을 `getUpdates`로 수신한다.
- **예비 PC (`standby`)는 전부** Telegram 명령 수신기를 끈다.
- 주 PC와 예비 PC 모두 CGV 좌석 감시와 Telegram `sendMessage` 알림 발송은 가능하다.
- 두 대가 동시에 `primary`이면 Telegram `409 Conflict`가 발생한다. 이 상태에서는 어느 PC가 명령을 받을지 보장되지 않는다.

`TELEGRAM_INSTANCE_ROLE`의 기본값은 안전을 위해 `standby`다. 값이 없거나 새 저장소를 clone한 PC는 명령 수신기를 시작하지 않는다.

## 최초 설정

주 PC에서:

```bash
./set_machine_role.sh primary
sh install_macos_service.sh
```

다른 모든 PC에서:

```bash
./set_machine_role.sh standby
sh install_macos_service.sh
```

예비 PC의 LaunchAgent 프로세스가 실행 후 정상 종료되는 것은 오류가 아니다. `standby machine` 로그가 한 줄 있으면 의도한 상태다.

## 장애 전환

1. 기존 주 PC가 꺼졌거나 네트워크에서 분리됐는지 확인한다.
2. 예비 PC 한 대에서만 `./set_machine_role.sh primary`를 실행한다.
3. `sh install_macos_service.sh`를 실행한다.
4. Telegram 봇에 `/status`를 보내 새 주 PC가 응답하는지 확인한다.
5. 이전 주 PC가 다시 켜지기 전 반드시 그 PC를 `standby`로 바꾼다. 원격 변경이 불가능하면 이전 PC를 네트워크에 연결하지 않은 상태에서 먼저 설정한다.

자동 감시 작업은 여러 PC에서 돌릴 수 있지만 같은 결과가 중복 전송될 수 있다. 평상시에는 주 PC만 15분 감시를 활성화하고, 예비 PC는 작업을 일시 중지해 두는 구성이 가장 안전하다. 주 PC 장애 시 예비 PC의 역할을 `primary`로 바꾸고 감시 작업을 활성화한다.

## 에이전트 확인 체크리스트

다른 PC의 에이전트는 작업을 시작하기 전에 다음을 확인한다.

1. `MULTI_PC_FAILOVER.md`, `AGENTS.md`, `OPERATIONS.md`를 읽는다.
2. `.env`의 실제 비밀값을 출력하지 않고 `TELEGRAM_INSTANCE_ROLE`만 확인한다.
3. 사용자가 명시적으로 주 PC 전환을 요청하지 않았다면 그 PC를 `standby`로 유지한다.
4. `409 Conflict`가 보이면 새 수신기를 더 실행하지 말고 모든 PC의 역할을 확인한다.
5. Telegram 토큰, Chat ID, CGV 쿠키, 결제 정보는 로그나 GitHub에 남기지 않는다.
