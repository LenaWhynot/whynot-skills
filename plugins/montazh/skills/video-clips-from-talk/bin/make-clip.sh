#!/usr/bin/env bash
# Один вертикальный ролик с вшитыми субтитрами.
#   make-clip.sh ИСХОДНИК СУБТИТРЫ.srt СТАРТ ДЛИТЕЛЬНОСТЬ ВЫХОД.mp4 [КРОП]
#   СТАРТ — 00:12:34 или 754   ·   ДЛИТЕЛЬНОСТЬ — секунды
#   КРОП  — center (по умолчанию) | left | right | число пикселей от левого края
set -e
SRC="$1"; SRT="$2"; START="$3"; DUR="$4"; OUT="$5"; CROP="${6:-center}"

[ -f "$SRC" ] || { echo "Нет исходника: $SRC"; exit 1; }
[ -f "$SRT" ] || { echo "Нет субтитров: $SRT"; exit 1; }
mkdir -p "$(dirname "$OUT")"

W=$(ffprobe -v error -select_streams v -show_entries stream=width  -of csv=p=0 "$SRC")
H=$(ffprobe -v error -select_streams v -show_entries stream=height -of csv=p=0 "$SRC")
CW=$(python3 -c "print(int($H*9/16))")
case "$CROP" in
  center) X=$(python3 -c "print(max(0,int(($W-$CW)/2)))") ;;
  left)   X=0 ;;
  right)  X=$(python3 -c "print(max(0,$W-$CW))") ;;
  *)      X="$CROP" ;;
esac

# ffmpeg отдаёт фильтру уже обрезанный кусок, и его время начинается с нуля,
# а в .srt время абсолютное — субтитры показались бы от начала записи.
# Поэтому режем и сдвигаем сами субтитры в отдельный временный файл.
TMPSRT="$(mktemp -t clipsub).srt"
trap 'rm -f "$TMPSRT"' EXIT
python3 - "$SRT" "$START" "$DUR" "$TMPSRT" <<'PY'
import re, sys
srt, start, dur, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]

def secs(v):
    if ":" not in v:
        return float(v)
    parts = [float(x.replace(",", ".")) for x in v.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]

def stamp(t):
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

t0, t1 = secs(start), secs(start) + dur
blocks = re.split(r"\n\s*\n", open(srt, encoding="utf-8-sig").read().strip())
kept = []
for b in blocks:
    lines = b.strip().split("\n")
    tl = next((l for l in lines if "-->" in l), None)
    if not tl:
        continue
    a, z = [secs(x.strip()) for x in tl.split("-->")]
    if z <= t0 or a >= t1:
        continue
    text = "\n".join(lines[lines.index(tl) + 1:]).strip()
    if text:
        kept.append((max(a, t0) - t0, min(z, t1) - t0, text))

with open(out, "w", encoding="utf-8") as f:
    for i, (a, z, text) in enumerate(kept, 1):
        f.write(f"{i}\n{stamp(a)} --> {stamp(z)}\n{text}\n\n")
print(f"  субтитров в куске: {len(kept)}")
PY

STYLE="FontSize=15,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=140"

ffmpeg -nostdin -y -v error -ss "$START" -i "$SRC" -t "$DUR" \
  -vf "crop=${CW}:${H}:${X}:0,scale=1080:1920,setsar=1,subtitles=${TMPSRT}:force_style='${STYLE}'" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart "$OUT"

printf 'Готов %s — %s с, %sx%s\n' "$OUT" \
  "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" | cut -d. -f1)" \
  "$(ffprobe -v error -select_streams v -show_entries stream=width  -of csv=p=0 "$OUT")" \
  "$(ffprobe -v error -select_streams v -show_entries stream=height -of csv=p=0 "$OUT")"
