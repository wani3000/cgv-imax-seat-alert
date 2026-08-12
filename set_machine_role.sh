#!/bin/sh
set -eu

ROLE=${1:-}
case "$ROLE" in
  primary|standby) ;;
  *) echo "사용법: $0 primary|standby" >&2; exit 2 ;;
esac

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo ".env 파일이 없어요." >&2
  exit 1
fi

TMP_FILE=$(mktemp "${TMPDIR:-/tmp}/cgv-imax-env.XXXXXX")
trap 'rm -f "$TMP_FILE"' EXIT HUP INT TERM
awk -v role="$ROLE" '
  BEGIN { replaced = 0 }
  /^TELEGRAM_INSTANCE_ROLE=/ { print "TELEGRAM_INSTANCE_ROLE=" role; replaced = 1; next }
  { print }
  END { if (!replaced) print "TELEGRAM_INSTANCE_ROLE=" role }
' "$ENV_FILE" > "$TMP_FILE"
install -m 600 "$TMP_FILE" "$ENV_FILE"

echo "이 PC의 Telegram 역할을 $ROLE(으)로 설정했어요."
echo "이제 sh install_macos_service.sh 를 실행해 적용하세요."

