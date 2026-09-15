#!/usr/bin/env bash
# Полоса из 6 кадров по всей длительности куска — что внутри, а не в его середине.
#   strip.sh ВИДЕО СТАРТ ДЛИТЕЛЬНОСТЬ ВЫХОД.png
set -e
SRC="$1"; START="$2"; DUR="$3"; OUT="$4"
[ -f "$SRC" ] || { echo "Нет файла: $SRC"; exit 1; }
mkdir -p "$(dirname "$OUT")"
FPS=$(python3 -c "print(6/$DUR)")
ffmpeg -nostdin -y -v error -ss "$START" -t "$DUR" -i "$SRC" \
  -vf "fps=${FPS},drawtext=text='%{pts\\:hms}':fontcolor=yellow:fontsize=20:box=1:boxcolor=black@0.85:x=4:y=4,scale=250:-1,tile=6x1:padding=3" \
  -frames:v 1 "$OUT"
echo "Полоса: $OUT"
