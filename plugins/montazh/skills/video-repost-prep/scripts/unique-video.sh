#!/usr/bin/env bash
# unique-video.sh — снимает метаданные с видео и делает N уникальных копий
# для повторной заливки одного и того же ролика (например, trial reels).
#
# Использование:
#   ./unique-video.sh video.mp4              # 3 варианта
#   ./unique-video.sh video.mp4 5            # 5 вариантов
#   ./unique-video.sh video.mp4 5 ~/out      # + своя папка для результата
#
# Переменные окружения:
#   STRONG=1      более сильная обработка (кроп 24/32/40px с каждого края
#                 для первых трёх копий, ускорение и срез начала) — когда мягкой не хватило
#   MAXDUR=59     обрезать до N секунд (инстаграм капризничает на длинных)
#   MIRROR=1      отразить по горизонтали — сильнее всего ломает отпечаток,
#                 но переворачивает текст на экране и лица. Проверь глазами!
#   PITCH=1       сдвинуть высоту звука на ~1% (голос почти не меняется,
#                 но аудио-отпечаток становится другим)
#
# Что делает с каждой копией:
#   1) отключает перенос входных метаданных через -map_metadata -1
#   2) микро-меняет картинку (кроп 2-8px + возврат к исходному размеру,
#      сдвиг яркости/насыщенности на доли процента) — глазом не видно,
#      эффект зависит от исходника; распознавание площадкой не гарантировано
#   3) меняет длительность и темп звука; параметры зависят от номера копии
#   4) кодирует H.264 с CRF 19 + (номер копии % 4)
# Результат — папка <имя>-unique/ рядом с исходником (или в указанной папке).

set -euo pipefail

SRC="${1:?укажи файл: ./unique-video.sh video.mp4 [сколько копий]}"
N="${2:-3}"
OUTROOT="${3:-}"
STRONG="${STRONG:-0}"
MIRROR="${MIRROR:-0}"
PITCH="${PITCH:-0}"
MAXDUR="${MAXDUR:-0}"

[ -f "$SRC" ] || { echo "нет такого файла: $SRC" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "нужен ffmpeg: brew install ffmpeg" >&2; exit 1; }

DIR=$(cd "$(dirname "$SRC")" && pwd)
BASE=$(basename "$SRC"); NAME="${BASE%.*}"
OUT="${OUTROOT:-$DIR}/$NAME-unique"; mkdir -p "$OUT"

W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$SRC")
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$SRC")
HAS_AUDIO=$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$SRC" | head -1)

echo "исходник: $BASE  (${W}x${H})"
echo "делаю $N вариантов → $OUT"

for i in $(seq 1 "$N"); do
  if [ "$STRONG" = "1" ]; then
    CROP=$(( 16 + i * 8 ))                           # зум зависит от размеров исходного кадра
    BR=$(printf '%.4f' "$(echo "scale=4; $i * 0.010 - 0.015" | bc)")
    SAT=$(printf '%.4f' "$(echo "scale=4; 1 + $i * 0.012" | bc)")
    PTS=$(printf '%.4f' "$(echo "scale=4; 1 - $i * 0.008" | bc)")
    SKIP=$(printf '%.2f' "$(echo "scale=2; 0.10 + $i * 0.07" | bc)")  # срез начала
    SUF="s${i}"
  else
    CROP=$(( i * 2 ))                                # 2,4,6... px по краям
    BR=$(printf '%.4f' "$(echo "scale=4; $i * 0.004 - 0.006" | bc)")
    SAT=$(printf '%.4f' "$(echo "scale=4; 1 + $i * 0.003" | bc)")
    PTS=$(printf '%.4f' "$(echo "scale=4; 1 - $i * 0.002" | bc)")
    SKIP=0
    SUF="v${i}"
  fi
  CW=$(( W - CROP * 2 )); CH=$(( H - CROP * 2 ))
  TEMPO=$(printf '%.4f' "$(echo "scale=4; 1 / $PTS" | bc)")          # темп звука
  CRF=$(( 19 + i % 4 ))
  DEST="$OUT/${NAME}-${SUF}.mp4"

  VF="crop=${CW}:${CH}:${CROP}:${CROP},scale=${W}:${H},eq=brightness=${BR}:saturation=${SAT}"
  [ "$MIRROR" = "1" ] && VF="${VF},hflip"
  VF="${VF},setpts=${PTS}*PTS"

  # звук: темп всегда, высота — по флагу
  if [ "$PITCH" = "1" ]; then
    SR=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of csv=p=0 "$SRC")
    RATE=$(printf '%.0f' "$(echo "scale=4; $SR * (1 + $i * 0.004)" | bc)")
    AF="asetrate=${RATE},aresample=${SR},atempo=$(printf '%.4f' "$(echo "scale=4; $TEMPO * $SR / $RATE" | bc)")"
  else
    AF="atempo=${TEMPO}"
  fi

  TRIM=()
  [ "$SKIP" != "0" ] && TRIM+=(-ss "$SKIP")
  [ "$MAXDUR" != "0" ] && TRIM+=(-t "$MAXDUR")

  if [ -n "$HAS_AUDIO" ]; then
    ffmpeg -hide_banner -loglevel error -y ${TRIM[@]+"${TRIM[@]}"} -i "$SRC" \
      -vf "$VF" -af "$AF" \
      -c:v libx264 -preset medium -crf "$CRF" -pix_fmt yuv420p \
      -c:a aac -b:a 128k \
      -map_metadata -1 -metadata:s:v handler_name= -metadata:s:a handler_name= \
      -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
      -movflags +faststart "$DEST"
  else
    ffmpeg -hide_banner -loglevel error -y ${TRIM[@]+"${TRIM[@]}"} -i "$SRC" \
      -vf "$VF" -an \
      -c:v libx264 -preset medium -crf "$CRF" -pix_fmt yuv420p \
      -map_metadata -1 -metadata:s:v handler_name= \
      -fflags +bitexact -flags:v +bitexact \
      -movflags +faststart "$DEST"
  fi

  # финально обнуляем дату файла в файловой системе
  touch -t "$(date -v-${i}d +%Y%m%d%H%M)" "$DEST" 2>/dev/null || true
  echo "  ✓ $SUF  crf=$CRF  crop=${CROP}px  темп=${PTS}  срез=${SKIP}s  $(du -h "$DEST" | cut -f1)"
done

echo "готово: $OUT"
