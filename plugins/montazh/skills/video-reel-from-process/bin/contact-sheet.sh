#!/usr/bin/env bash
# Контактные листы по всей съёмке: кадры с подписью времени, по 24 на лист.
#   contact-sheet.sh СЪЁМКА.mp4 ПАПКА [СКОЛЬКО_КАДРОВ]
set -e
SRC="$1"; DIR="${2:-листы}"; N="${3:-72}"
[ -f "$SRC" ] || { echo "Нет файла: $SRC"; exit 1; }
mkdir -p "$DIR"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
STEP=$(python3 -c "print(max(0.5, $DUR/$N))")
echo "Длительность $(python3 -c "print(int($DUR))") с, беру кадр каждые $(python3 -c "print(round($STEP,1))") с"

ffmpeg -nostdin -y -v error -i "$SRC" \
  -vf "fps=1/${STEP},drawtext=text='%{pts\\:hms}':fontcolor=yellow:fontsize=22:box=1:boxcolor=black@0.85:x=6:y=6,scale=320:-1,tile=6x4:padding=4" \
  -frames:v 100 "$DIR/лист_%02d.png"

echo "Готово. Листы в $DIR/ — посмотрите их и выпишите, что происходит и когда."
ls "$DIR"
