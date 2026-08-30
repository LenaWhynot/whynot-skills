#!/usr/bin/env bash
# Локальное распознавание речи: свой venv, ничего в системный python не лезет.
# Ставится один раз, минут двадцать. Модель качается при первом запуске.
set -e
DIR="$HOME/.whynot-asr"
VENV="$DIR/.venv"

command -v python3 >/dev/null || { echo "Нет python3. macOS: brew install python; Windows: winget install Python.Python.3"; exit 1; }

mkdir -p "$DIR"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
echo "Ставлю faster-whisper (несколько минут)…"
"$VENV/bin/python" -m pip install faster-whisper

echo
echo "Готово. Проверка:"
"$VENV/bin/python" -c "import faster_whisper; print('  faster-whisper', faster_whisper.__version__)"
echo "Модель скачается сама при первой расшифровке (~1,5 ГБ, один раз)."
