#!/usr/bin/env bash
# Сборка вертикального ролика по раскладке.
#   assemble.sh СЪЁМКА.mp4 РАСКЛАДКА.txt ВЫХОД.mp4 [КРОП]
#   в раскладке по строке на кусок: «старт длительность» (секунды)
set -e
SRC="$1"; PLAN="$2"; OUT="$3"; CROP="${4:-center}"
[ -f "$SRC" ]  || { echo "Нет файла: $SRC"; exit 1; }
[ -f "$PLAN" ] || { echo "Нет раскладки: $PLAN"; exit 1; }

W=$(ffprobe -v error -select_streams v -show_entries stream=width  -of csv=p=0 "$SRC")
H=$(ffprobe -v error -select_streams v -show_entries stream=height -of csv=p=0 "$SRC")
CW=$(python3 -c "print(int($H*9/16))")
case "$CROP" in
  center) X=$(python3 -c "print(max(0,int(($W-$CW)/2)))") ;;
  left)   X=0 ;;
  right)  X=$(python3 -c "print(max(0,$W-$CW))") ;;
  *)      X="$CROP" ;;
esac

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
I=0
while read -r START DUR _; do
  case "$START" in ''|'#'*) continue ;; esac
  I=$((I+1))
  printf '  кусок %02d — %s с от %s\n' "$I" "$DUR" "$START"
  ffmpeg -nostdin -y -v error -ss "$START" -i "$SRC" -t "$DUR" \
    -vf "crop=${CW}:${H}:${X}:0,scale=1080:1920,setsar=1,fps=30" -an \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$TMP/$(printf '%03d' $I).mp4"
  printf "file '%s'\n" "$TMP/$(printf '%03d' $I).mp4" >> "$TMP/list.txt"
done < "$PLAN"

[ "$I" -gt 0 ] || { echo "В раскладке нет ни одного куска"; exit 1; }
mkdir -p "$(dirname "$OUT")"
ffmpeg -nostdin -y -v error -f concat -safe 0 -i "$TMP/list.txt" -c copy "$OUT"

printf 'Готов %s — %s кусков, %s с, %sx%s\n' "$OUT" "$I" \
  "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" | cut -d. -f1)" \
  "$(ffprobe -v error -select_streams v -show_entries stream=width  -of csv=p=0 "$OUT")" \
  "$(ffprobe -v error -select_streams v -show_entries stream=height -of csv=p=0 "$OUT")"
