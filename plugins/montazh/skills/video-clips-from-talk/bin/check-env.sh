#!/usr/bin/env bash
# Что уже стоит, а чего не хватает. Ничего не устанавливает — только смотрит.
ok()   { printf '  ✅ %s\n' "$1"; }
nope() { printf '  ❌ %s\n' "$1"; }

echo "Проверяю окружение:"
command -v ffmpeg  >/dev/null && ok "ffmpeg  $(ffmpeg -version | head -1 | cut -d' ' -f3)" || nope "ffmpeg — без него нельзя резать видео"
command -v ffprobe >/dev/null && ok "ffprobe" || nope "ffprobe (обычно ставится вместе с ffmpeg)"
command -v python3 >/dev/null && ok "python3 $(python3 -V 2>&1 | cut -d' ' -f2)" || nope "python3 — нужен для распознавания речи"

VENV="$HOME/.whynot-asr/.venv"
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import faster_whisper" 2>/dev/null; then
  ok "локальное распознавание речи готово ($VENV)"
else
  nope "локального распознавания нет — поставить: bash bin/setup-local-asr.sh (или выбрать облачный путь)"
fi

echo
echo "Если чего-то не хватает — команды установки ffmpeg:"
echo "  macOS:   brew install ffmpeg"
echo "  Windows: winget install Gyan.FFmpeg"
echo "  Linux:   sudo apt install ffmpeg"
