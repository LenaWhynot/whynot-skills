#!/usr/bin/env bash
# Публикация в свой Instagram напрямую через Graph API. Без сервисов-посредников.
# Meta СКАЧИВАЕТ медиа сама по публичной ссылке — локальный файл ей не отдать.
set -uo pipefail

CONF="${WHYNOT_IG_CONF:-$HOME/.config/whynot/instagram.env}"
API="https://graph.instagram.com"

usage() {
  cat <<TXT
Использование:
  to-instagram.sh --limit                       сколько постов ещё можно за сутки
  to-instagram.sh <URL> ["подпись"] [--reel|--photo]

<URL> — ПУБЛИЧНАЯ прямая ссылка на файл, которую откроет кто угодно без входа.
Локальный путь и ссылка на страницу Google Drive не годятся: Meta скачивает
файл сама и логиниться не умеет. Куда класть файл — см. rail-instagram.md.

Тип определяется по расширению, --reel и --photo нужны, только если спорно.
Настройки: $CONF  (IG_USER_ID, IG_ACCESS_TOKEN)
TXT
}

[ $# -eq 0 ] && { usage; exit 1; }
[ -f "$CONF" ] || { echo "❌ нет файла настроек: $CONF"; echo; usage; exit 1; }
# shellcheck disable=SC1090
set -a; . "$CONF"; set +a
: "${IG_USER_ID:?в $CONF нет IG_USER_ID}"
: "${IG_ACCESS_TOKEN:?в $CONF нет IG_ACCESS_TOKEN}"

jget() { RESP="$1" KEY="$2" python3 -c '
import json,os,sys
try: d=json.loads(os.environ["RESP"])
except Exception: sys.exit(1)
cur=d
for part in os.environ["KEY"].split("."):
    if isinstance(cur,dict) and part in cur: cur=cur[part]
    elif isinstance(cur,list) and part.isdigit() and int(part)<len(cur): cur=cur[int(part)]
    else: sys.exit(1)
print(cur)'; }

if [ "$1" = "--limit" ]; then
  R=$(curl -sS --max-time 30 --get "$API/$IG_USER_ID/content_publishing_limit" \
        --data-urlencode "fields=quota_usage,config" \
        --data-urlencode "access_token=$IG_ACCESS_TOKEN")
  USED=$(jget "$R" "data.0.quota_usage") || { echo "❌ не ответил: $(jget "$R" "error.message" || echo "$R" | head -c 200)"; exit 1; }
  CAP=$(jget "$R" "data.0.config.quota_total" || echo "?")
  echo "✅ за последние сутки опубликовано $USED из $CAP"
  exit 0
fi

URL="$1"; CAPTION="${2:-}"; FORCE="${3:-}"
case "$URL" in
  http://*|https://*) ;;
  *) echo "❌ нужна публичная ссылка, а не путь к файлу: $URL"; echo; usage; exit 1 ;;
esac
case "$URL" in
  *drive.google.com/file/*)
    echo "❌ это ссылка на СТРАНИЦУ Google Drive, а не на файл — Meta по ней получит HTML."
    echo "   Нужна прямая ссылка на сам файл. См. rail-instagram.md, раздел про хостинг."
    exit 1 ;;
esac

if [ -n "$CAPTION" ]; then
  LEN=$(CAP="$CAPTION" python3 -c 'import os;print(len(os.environ["CAP"]))')
  [ "$LEN" -gt 2200 ] && { echo "❌ подпись $LEN знаков — у Instagram предел 2200."; exit 1; }
fi

case "$FORCE" in
  --reel)  KIND=reel ;;
  --photo) KIND=photo ;;
  *) case "${URL##*.}" in
       mp4|mov|m4v|MP4|MOV|M4V) KIND=reel ;;
       jpg|jpeg|JPG|JPEG) KIND=photo ;;
       png|PNG) echo "❌ Instagram не принимает PNG по ссылке — переведи в JPEG"; exit 1 ;;
       *) echo "❌ не понял тип по ссылке. Добавь --reel или --photo"; exit 1 ;;
     esac ;;
esac

# 1. Контейнер
ARGS=( -sS --max-time 120 -X POST "$API/$IG_USER_ID/media"
       --data-urlencode "access_token=$IG_ACCESS_TOKEN" )
if [ "$KIND" = "reel" ]; then
  ARGS+=( --data-urlencode "media_type=REELS" --data-urlencode "video_url=$URL" )
else
  ARGS+=( --data-urlencode "image_url=$URL" )
fi
[ -n "$CAPTION" ] && ARGS+=( --data-urlencode "caption=$CAPTION" )

R=$(curl "${ARGS[@]}")
CID=$(jget "$R" "id") || { echo "❌ Instagram не принял: $(jget "$R" "error.message" || echo "$R" | head -c 300)"; exit 1; }
echo "→ контейнер $CID создан, жду обработки"

# 2. Ждём готовности. Видео Meta обрабатывает не мгновенно.
for i in $(seq 1 60); do
  S=$(curl -sS --max-time 30 --get "$API/$CID" \
        --data-urlencode "fields=status_code,status" \
        --data-urlencode "access_token=$IG_ACCESS_TOKEN")
  ST=$(jget "$S" "status_code" || echo "")
  case "$ST" in
    FINISHED) echo "→ готов"; break ;;
    ERROR)    echo "❌ Meta не смогла обработать файл: $(jget "$S" "status" || echo "причина не названа")"
              echo "   Чаще всего — ссылка не открывается снаружи или формат не подходит."; exit 1 ;;
    EXPIRED)  echo "❌ контейнер протух, не дождавшись публикации"; exit 1 ;;
  esac
  [ "$i" = 60 ] && { echo "❌ обработка не закончилась за 5 минут"; exit 1; }
  sleep 5
done

# 3. Публикация
R=$(curl -sS --max-time 60 -X POST "$API/$IG_USER_ID/media_publish" \
      --data-urlencode "creation_id=$CID" \
      --data-urlencode "access_token=$IG_ACCESS_TOKEN")
MID=$(jget "$R" "id") || { echo "❌ опубликовать не вышло: $(jget "$R" "error.message" || echo "$R" | head -c 300)"; exit 1; }
echo "✅ опубликовано, id записи $MID"
