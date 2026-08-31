#!/usr/bin/env bash
# Сторож токена Instagram: смотрит срок, обновляет, ставит расписание.
# Токен живёт 60 дней. Пропустил срок — обновить уже нельзя, только заводить заново.
set -uo pipefail

CONF="${WHYNOT_IG_CONF:-$HOME/.config/whynot/instagram.env}"
LOG="$(dirname "$CONF")/ig-token.log"

usage() {
  cat <<TXT
Использование:
  ig-token.sh --status      сколько токену осталось жить
  ig-token.sh --refresh     обновить токен и перезаписать файл
  ig-token.sh --schedule    обновлять самому раз в неделю (macOS, launchd)
  ig-token.sh --unschedule  убрать расписание

Файл настроек: $CONF
  IG_USER_ID=17841400000000000
  IG_ACCESS_TOKEN=IGQ...
  IG_TOKEN_EXPIRES=1767225600     ← ставится автоматически при обновлении
TXT
}

[ $# -eq 0 ] && { usage; exit 1; }

need_conf() {
  [ -f "$CONF" ] || { echo "❌ нет файла настроек: $CONF"; echo; usage; exit 1; }
  # shellcheck disable=SC1090
  set -a; . "$CONF"; set +a
  : "${IG_ACCESS_TOKEN:?в $CONF нет IG_ACCESS_TOKEN}"
}

# Перезапись без потери токена: пишем во временный файл и подменяем целиком.
set_key() {
  local key="$1" val="$2" tmp
  tmp="$(mktemp "${CONF}.XXXXXX")" || return 1
  if grep -q "^${key}=" "$CONF"; then
    KEY="$key" VAL="$val" python3 -c '
import os,sys,io
k=os.environ["KEY"]; v=os.environ["VAL"]
out=[]
for line in io.open(sys.argv[1],encoding="utf-8"):
    out.append(k+"="+v+"\n" if line.startswith(k+"=") else line)
io.open(sys.argv[2],"w",encoding="utf-8").writelines(out)
' "$CONF" "$tmp" || { rm -f "$tmp"; return 1; }
  else
    cp "$CONF" "$tmp" || { rm -f "$tmp"; return 1; }
    printf '%s=%s\n' "$key" "$val" >> "$tmp"
  fi
  chmod 600 "$tmp" && mv "$tmp" "$CONF"
}

days_left() {
  [ -n "${IG_TOKEN_EXPIRES:-}" ] || { echo ""; return; }
  echo $(( ( IG_TOKEN_EXPIRES - $(date +%s) ) / 86400 ))
}

case "$1" in
--status)
  need_conf
  D="$(days_left)"
  if [ -z "$D" ]; then
    echo "⚠️  срок неизвестен — в файле нет IG_TOKEN_EXPIRES."
    echo "   Запусти: ig-token.sh --refresh — он проставит срок сам."
    exit 0
  fi
  if   [ "$D" -lt 0 ]; then echo "❌ токен протух $(( -D )) дн. назад — обновить уже нельзя, нужен новый"; exit 1
  elif [ "$D" -lt 10 ]; then echo "⚠️  токену осталось $D дн. — обнови сейчас: ig-token.sh --refresh"
  else echo "✅ токен живёт ещё $D дн."; fi
  ;;

--refresh)
  need_conf
  RESP=$(curl -sS --max-time 60 --get "https://graph.instagram.com/refresh_access_token" \
    --data-urlencode "grant_type=ig_refresh_token" \
    --data-urlencode "access_token=$IG_ACCESS_TOKEN")

  NEW=$(RESP="$RESP" python3 -c '
import json,os
d=json.loads(os.environ["RESP"])
if "access_token" in d:
    print(d["access_token"], d.get("expires_in", 0))
' 2>/dev/null)

  if [ -z "$NEW" ]; then
    ERR=$(RESP="$RESP" python3 -c '
import json,os
d=json.loads(os.environ["RESP"])
print(d.get("error",{}).get("message","непонятный ответ"))
' 2>/dev/null || echo "непонятный ответ")
    echo "❌ обновить не вышло: $ERR"
    printf '%s\tОШИБКА\t%s\n' "$(date -u +%FT%TZ)" "$ERR" >> "$LOG"
    exit 1
  fi

  TOKEN="${NEW%% *}"; SECS="${NEW##* }"
  EXP=$(( $(date +%s) + SECS ))
  set_key IG_ACCESS_TOKEN "$TOKEN" || { echo "❌ не смог записать новый токен в $CONF"; exit 1; }
  set_key IG_TOKEN_EXPIRES "$EXP"  || { echo "⚠️  токен записан, а срок нет"; }
  printf '%s\tOK\tещё %s дн.\n' "$(date -u +%FT%TZ)" "$(( SECS / 86400 ))" >> "$LOG"
  echo "✅ обновлён, живёт ещё $(( SECS / 86400 )) дн."
  ;;

--schedule)
  [ "$(uname -s)" = "Darwin" ] || { echo "❌ расписание умею ставить только на macOS"; exit 1; }
  SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  PL="$HOME/Library/LaunchAgents/ru.whynot.ig-token.plist"
  mkdir -p "$(dirname "$PL")"
  cat > "$PL" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ru.whynot.ig-token</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$SELF</string><string>--refresh</string></array>
  <key>StartInterval</key><integer>604800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PLIST
  launchctl unload "$PL" 2>/dev/null
  launchctl load "$PL" 2>/dev/null && echo "✅ буду обновлять раз в неделю. Журнал: $LOG" \
    || { echo "❌ launchctl не принял задание"; exit 1; }
  ;;

--unschedule)
  PL="$HOME/Library/LaunchAgents/ru.whynot.ig-token.plist"
  launchctl unload "$PL" 2>/dev/null
  rm -f "$PL" && echo "✅ расписание убрано"
  ;;

*) usage; exit 1 ;;
esac
