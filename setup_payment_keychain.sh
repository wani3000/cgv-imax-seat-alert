#!/bin/sh
set -eu

ACCOUNT="cgv-imax-seat-alert"

printf '토스 가입 휴대폰 번호를 숫자만 입력하세요: '
stty -echo
IFS= read -r PHONE
stty echo
printf '\n생년월일 6자리를 입력하세요: '
stty -echo
IFS= read -r BIRTHDATE
stty echo
printf '\n'

case "$PHONE" in
  *[!0-9]*|'') echo "휴대폰 번호는 숫자만 입력해야 해요." >&2; exit 1 ;;
esac
case "$BIRTHDATE" in
  *[!0-9]*|'') echo "생년월일은 숫자 6자리여야 해요." >&2; exit 1 ;;
esac
if [ "${#PHONE}" -lt 10 ] || [ "${#PHONE}" -gt 11 ]; then
  echo "휴대폰 번호 길이를 확인해 주세요." >&2
  exit 1
fi
if [ "${#BIRTHDATE}" -ne 6 ]; then
  echo "생년월일은 숫자 6자리여야 해요." >&2
  exit 1
fi

/usr/bin/security add-generic-password -U -a "$ACCOUNT" -s "cgv-imax-seat-alert.toss-phone" -w "$PHONE"
/usr/bin/security add-generic-password -U -a "$ACCOUNT" -s "cgv-imax-seat-alert.toss-birthdate" -w "$BIRTHDATE"
unset PHONE BIRTHDATE
echo "토스 결제 식별 정보를 macOS 키체인에 저장했어요."

