#!/usr/bin/env bash
# Ставит ffmpeg и ffprobe БЕЗ Homebrew и БЕЗ пароля администратора.
# Ничего системного не трогает: кладёт два файла в свою папку.
set -uo pipefail

DEST="${1:-$HOME/.whynot-bin}"
REPO="descriptinc/ffmpeg-ffprobe-static"

have() { command -v "$1" >/dev/null 2>&1; }

if have ffmpeg && have ffprobe; then
  echo "✅ уже стоит: $(command -v ffmpeg)"
  ffmpeg -version | head -1
  exit 0
fi

if [ -x "$DEST/ffmpeg" ] && [ -x "$DEST/ffprobe" ]; then
  echo "✅ уже скачано раньше: $DEST"
  exit 0
fi

# Homebrew уже стоит — самый чистый путь, пароль он не спросит
if have brew; then
  echo "→ нашёл Homebrew, ставлю через него"
  if brew install ffmpeg; then exit 0; fi
  echo "⚠️  brew не справился, перехожу на статическую сборку"
fi

OS="$(uname -s)"; ARCH="$(uname -m)"
case "$OS/$ARCH" in
  Darwin/arm64)  PLAT="darwin-arm64" ;;
  Darwin/x86_64) PLAT="darwin-x64"   ;;
  Linux/x86_64)  PLAT="linux-x64"    ;;
  Linux/aarch64) PLAT="linux-arm64"  ;;
  *)
    echo "❌ готовой сборки под $OS/$ARCH у меня нет."
    echo "   Windows: winget install Gyan.FFmpeg"
    echo "   Linux:   sudo apt install ffmpeg"
    exit 1 ;;
esac

echo "→ качаю ffmpeg и ffprobe для $PLAT"
echo "  источник: публичные релизы github.com/$REPO (~50 МБ)"
echo "  кладу в $DEST — прав администратора не нужно"

mkdir -p "$DEST" || exit 1

for TOOL in ffmpeg ffprobe; do
  URL=$(curl -fsSL --max-time 30 "https://api.github.com/repos/$REPO/releases/latest" \
    | ASSET="$TOOL-$PLAT" python3 -c \
      'import json,os,sys;d=json.load(sys.stdin);n=os.environ["ASSET"];print(next(a["browser_download_url"] for a in d["assets"] if a["name"]==n))') || {
    echo "❌ не смог узнать адрес для $TOOL"; exit 1; }

  echo "  … $TOOL"
  curl -fL --progress-bar --max-time 900 -o "$DEST/$TOOL" "$URL" || { echo "❌ не скачался $TOOL"; exit 1; }
  chmod +x "$DEST/$TOOL"
  [ "$OS" = "Darwin" ] && xattr -d com.apple.quarantine "$DEST/$TOOL" 2>/dev/null
done

if "$DEST/ffmpeg" -version >/dev/null 2>&1 && "$DEST/ffprobe" -version >/dev/null 2>&1; then
  echo "✅ готово: $DEST/ffmpeg и $DEST/ffprobe"
  "$DEST/ffmpeg" -version | head -1
  echo
  echo "Чтобы вызывались просто по имени, добавь в ~/.zshrc строку:"
  echo "  export PATH=\"$DEST:\$PATH\""
else
  echo "❌ скачалось, но не запускается — возможно, файл повреждён"
  exit 1
fi
