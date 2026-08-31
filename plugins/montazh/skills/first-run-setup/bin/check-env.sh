#!/usr/bin/env bash
# Что уже готово для монтажа и публикации. Ничего не ставит — только смотрит.
ok()   { printf '  ✅ %s\n' "$1"; }
nope() { printf '  ❌ %s\n' "$1"; }

echo "Смотрю, что уже есть на этом компьютере:"

if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg $(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3)"
elif [ -x "$HOME/.whynot-bin/ffmpeg" ]; then
  ok "ffmpeg в ~/.whynot-bin (не в PATH — вызывать по полному пути)"
else
  nope "ffmpeg — без него нельзя резать видео"
fi

command -v ffprobe >/dev/null 2>&1 || [ -x "$HOME/.whynot-bin/ffprobe" ] \
  && ok "ffprobe" || nope "ffprobe — обычно ставится вместе с ffmpeg"

command -v python3 >/dev/null 2>&1 \
  && ok "python3 $(python3 -V 2>&1 | cut -d' ' -f2)" \
  || nope "python3 — нужен для распознавания речи"

DRIVE=""
for CAND in "$HOME/Library/CloudStorage"/GoogleDrive-*/"My Drive" \
            "$HOME/Google Drive/My Drive" "$HOME/GoogleDrive/My Drive"; do
  [ -d "$CAND" ] && { DRIVE="$CAND"; break; }
done
if [ -n "$DRIVE" ]; then
  ok "Google Drive для десктопа подключён"
  [ -d "$DRIVE/publish" ] && ok "папка-шлюз publish уже есть" || nope "папки publish ещё нет — создастся при первой публикации"
else
  nope "Google Drive для десктопа не найден — через него ролик попадает в постинг"
fi

echo
echo "Чего я отсюда НЕ вижу и надо проверить обращением:"
echo "  · коннектор Metricool  — вызвать getBrandSettings"
echo "  · коннектор Google Drive — попробовать найти любой файл"
