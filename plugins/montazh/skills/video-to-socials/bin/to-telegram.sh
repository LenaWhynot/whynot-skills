#!/usr/bin/env bash
# Публикация в свой канал Telegram напрямую через Bot API.
# Бесплатно, без сервисов и без сервера. Токен читается из файла, не из аргументов.
set -uo pipefail

CONF="${WHYNOT_TG_CONF:-$HOME/.config/whynot/telegram.env}"

usage() {
  cat <<TXT
Использование:
  to-telegram.sh --check              проверить бота и канал, ничего не отправляя
  to-telegram.sh файл ["подпись"]     отправить видео или картинку в канал

Настройка (делается один раз):
  1. В Telegram напишите @BotFather → /newbot → получите токен
  2. Добавьте бота администратором в свой канал, с правом публикации
  3. Впишите оба значения в $CONF :
       TG_BOT_TOKEN=123456:AA...
       TG_CHAT_ID=@moy_kanal
Токен нигде не показывается и не передаётся в переписку.
TXT
}

[ $# -eq 0 ] && { usage; exit 1; }

if [ ! -f "$CONF" ]; then
  echo "❌ нет файла настроек: $CONF"
  echo
  usage
  exit 1
fi

# shellcheck disable=SC1090
set -a; . "$CONF"; set +a

: "${TG_BOT_TOKEN:?в $CONF нет TG_BOT_TOKEN}"
: "${TG_CHAT_ID:?в $CONF нет TG_CHAT_ID}"

API="https://api.telegram.org/bot$TG_BOT_TOKEN"

if [ "$1" = "--check" ]; then
  NAME=$(curl -sS --max-time 20 "$API/getMe" \
    | python3 -c 'import json,sys
d=json.load(sys.stdin)
print(d["result"]["username"] if d.get("ok") else "")' 2>/dev/null)
  [ -n "$NAME" ] || { echo "❌ токен не принят Telegram"; exit 1; }
  echo "✅ бот на связи: @$NAME"

  TITLE=$(curl -sS --max-time 20 --get "$API/getChat" --data-urlencode "chat_id=$TG_CHAT_ID" \
    | python3 -c 'import json,sys
d=json.load(sys.stdin)
print(d["result"].get("title","") if d.get("ok") else "")' 2>/dev/null)
  [ -n "$TITLE" ] || { echo "❌ канал $TG_CHAT_ID не виден — бот не добавлен админом?"; exit 1; }
  echo "✅ канал виден: $TITLE"
  exit 0
fi

SRC="$1"
CAPTION="${2:-}"
[ -f "$SRC" ] || { echo "❌ нет файла: $SRC"; exit 1; }

SIZE=$(stat -f%z "$SRC" 2>/dev/null || stat -c%s "$SRC" 2>/dev/null || echo 0)
if [ "$SIZE" -gt 52428800 ]; then
  echo "❌ файл $(( SIZE / 1048576 )) МБ — бот отправляет максимум 50 МБ."
  echo "   Пережмите ролик или выложите этот файл вручную."
  exit 1
fi

case "${SRC##*.}" in
  mp4|mov|m4v|MP4|MOV|M4V) METHOD=sendVideo; FIELD=video ;;
  jpg|jpeg|png|JPG|JPEG|PNG) METHOD=sendPhoto; FIELD=photo ;;
  *) echo "❌ не знаю, как отправить .${SRC##*.} — только видео и картинки"; exit 1 ;;
esac

# Считаем ЗНАКИ, а не байты: в кириллице байт вдвое больше, и bash соврёт.
if [ -n "$CAPTION" ]; then
  LEN=$(CAP="$CAPTION" python3 -c 'import os;print(len(os.environ["CAP"]))')
  if [ "$LEN" -gt 1024 ]; then
    echo "❌ подпись $LEN знаков — у Telegram предел 1024 для подписи к медиа."
    echo "   Сократите или отправьте текст отдельным сообщением после ролика."
    exit 1
  fi
fi

# Аргументы собираем массивом: подстановка ${VAR:+-F "..."} разъезжается
# по пробелам и ломает и подпись, и путь с пробелом в имени папки.
# --form-string, а не -F, для всего кроме самого файла.
# У curl в -F значение, начинающееся с @, означает «прочитай файл» —
# а имя канала в Telegram ВСЕГДА начинается с @. С -F публикация не работает вообще.
ARGS=( -sS --max-time 900 -X POST "$API/$METHOD"
       --form-string "chat_id=$TG_CHAT_ID"
       -F "$FIELD=@$SRC" )
if [ -n "$CAPTION" ]; then
  ARGS+=( --form-string "caption=$CAPTION" --form-string "parse_mode=HTML" )
fi

RESP=$(curl "${ARGS[@]}")

echo "$RESP" | python3 -c 'import json,sys
d=json.load(sys.stdin)
if d.get("ok"):
    m=d["result"]
    print("✅ опубликовано, сообщение №%s" % m.get("message_id"))
else:
    print("❌ Telegram отказал: %s" % d.get("description","непонятно"))
    sys.exit(1)'
