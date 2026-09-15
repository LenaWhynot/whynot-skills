#!/usr/bin/env bash
# Разворачивает проект моушен-графики на Remotion РЯДОМ с вашим заказом.
# Сам Remotion в наборе не лежит — он скачивается сюда при установке.
#
#   bash setup-remotion.sh [папка]     по умолчанию ./motion
#
# Дальше:
#   cd motion && npx remotion studio          посмотреть и подвигать
#   npx remotion render ClaudeEdit out/overlay.mov --codec=prores --prores-profile=4444
set -uo pipefail

DEST="${1:-./motion}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "ЛИЦЕНЗИЯ, скажу сразу: Remotion бесплатен для физических лиц и компаний"
echo "до 3 сотрудников. Компаниям больше нужна платная Company License."
echo "Это решение принимаете вы: проверить и купить лицензию скрипт за вас не может."
echo "Всё остальное в этом наборе таких требований не имеет и работает на ffmpeg."
echo ""

command -v node >/dev/null 2>&1 || { echo "Нет Node.js. Поставьте его с nodejs.org (LTS) и запустите снова."; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "Нет npm — он идёт вместе с Node.js."; exit 1; }
echo "Node $(node -v), npm $(npm -v)"

if [ -d "$DEST/node_modules" ]; then
  echo "✅ проект уже развёрнут: $DEST"
  exit 0
fi

mkdir -p "$DEST/src" "$DEST/out" "$DEST/public"
cp -R "$HERE/template/src/." "$DEST/src/"
cp -R "$HERE/template/public/." "$DEST/public/"   # демо-раскадровка, чтобы студия открылась

cat > "$DEST/package.json" <<'JSON'
{
  "name": "motion",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "studio": "remotion studio",
    "render": "remotion render"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.481",
    "@remotion/google-fonts": "^4.0.481",
    "@remotion/layout-utils": "^4.0.481",
    "react": "^19.2.7",
    "react-dom": "^19.2.7",
    "remotion": "^4.0.481"
  }
}
JSON

cat > "$DEST/remotion.config.ts" <<'TS'
import { Config } from "@remotion/cli/config";
Config.setVideoImageFormat("png");   // альфа в кадрах — оверлей кладётся поверх футажа
Config.setPixelFormat("yuva444p10le");
TS

cat > "$DEST/tsconfig.json" <<'JSON'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
JSON

echo "→ ставлю зависимости (первый раз это несколько минут и ~700 МБ)"
( cd "$DEST" && npm install --silent ) || { echo "npm install не прошёл — смотрите вывод выше"; exit 1; }

echo ""
echo "✅ готово: $DEST"
echo ""
echo "Посмотреть и подвигать:   cd $DEST && npx remotion studio"
echo "Отрендерить оверлей:      npx remotion render ClaudeEdit out/overlay.mov \\"
echo "                            --codec=prores --prores-profile=4444"
echo ""
echo "Дальше оверлей кладётся на футаж одной командой ffmpeg — она в SKILL.md навыка."
