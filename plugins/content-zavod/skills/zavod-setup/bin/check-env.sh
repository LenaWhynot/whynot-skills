#!/usr/bin/env bash
# Что уже есть на этом компьютере для контент-завода.
set -uo pipefail
ok()   { printf '  ✅ %s\n' "$1"; }
nope() { printf '  ❌ %s\n' "$1"; }
PY_BIN="${ZAVOD_PY:-python3}"

echo "Смотрю, что уже стоит:"
command -v ffmpeg  >/dev/null 2>&1 && ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')" || nope "ffmpeg — обязателен, поставлю сама"
command -v ffprobe >/dev/null 2>&1 && ok "ffprobe" || nope "ffprobe — идёт вместе с ffmpeg"
command -v "$PY_BIN" >/dev/null 2>&1 && ok "$($PY_BIN -V 2>&1)" || nope "python3 — нужен для монтажа и панелей"

"$PY_BIN" - <<'PY' 2>/dev/null || true
mods = {"faster_whisper": "расшифровка речи", "PIL": "карточки-панели", "numpy": "карточки-панели"}
for m, why in mods.items():
    try:
        __import__(m); print(f"  ✅ {m} — {why}")
    except ImportError:
        print(f"  ❌ {m} — {why}")
PY

echo ""
echo "Чего не хватает — ставится так:"
echo "  ffmpeg:    bash bin/setup-ffmpeg.sh   (без пароля администратора)"
echo "  остальное: $PY_BIN -m pip install --user faster-whisper pillow numpy"
