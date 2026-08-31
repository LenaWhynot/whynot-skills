#!/usr/bin/env bash
# Кладёт готовый файл в папку-шлюз внутри Google Drive.
# Оттуда Metricool заберёт его по ссылке — сам файл никуда больше не едет.
set -uo pipefail

SRC="${1:-}"
[ -n "$SRC" ] || { echo "❌ укажи файл: to-drive.sh рилс.mp4"; exit 1; }
[ -f "$SRC" ] || { echo "❌ файла нет: $SRC"; exit 1; }

DRIVE=""
for CAND in "$HOME/Library/CloudStorage"/GoogleDrive-*/"My Drive" \
            "$HOME/Google Drive/My Drive" \
            "$HOME/GoogleDrive/My Drive"; do
  [ -d "$CAND" ] && { DRIVE="$CAND"; break; }
done

if [ -z "$DRIVE" ]; then
  echo "❌ не нашёл подключённый Google Drive на этом компьютере."
  echo "   Нужна программа Google Drive для десктопа — после установки"
  echo "   диск появится как папка, и файлы будут уезжать сами."
  exit 1
fi

PUB="$DRIVE/publish"
mkdir -p "$PUB" || { echo "❌ не смог создать $PUB"; exit 1; }

BASE="$(basename "$SRC")"
cp "$SRC" "$PUB/$BASE" || { echo "❌ не смог скопировать"; exit 1; }

SIZE=$(stat -f%z "$PUB/$BASE" 2>/dev/null || stat -c%s "$PUB/$BASE" 2>/dev/null || echo 0)
if [ "$SIZE" -ge 1048576 ]; then
  HUMAN="$(( SIZE / 1048576 )) МБ"
else
  HUMAN="$(( SIZE / 1024 )) КБ"
fi

echo "✅ положил в шлюз: $PUB/$BASE ($HUMAN)"
echo
echo "Google Drive синхронизирует файл сам — обычно секунды, для тяжёлого видео дольше."
echo "Дальше: найди файл через коннектор Google Drive и возьми ссылку вида"
echo "  https://drive.google.com/file/d/<id>/view"
echo "Не нашёлся сразу — подожди и поищи ещё раз, это ещё идёт загрузка."
