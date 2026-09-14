#!/usr/bin/env bash
# Установка навыков монтажа в Codex.
#
# В Claude Code этот набор ставится плагином. Codex плагины Claude Code не читает,
# зато читает навыки из своей папки skills — этот скрипт их туда и кладёт,
# заодно переписывая пути под переменные Codex.
#
# Запуск:  bash install-codex.sh
# Снести:  bash install-codex.sh --remove

set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST="$CODEX_HOME/skills"
SKILLS=(first-run-setup video-clips-from-talk video-reel-from-process video-to-socials montazher)

say() { printf '%s\n' "$*"; }
die() { printf 'Не получилось: %s\n' "$*" >&2; exit 1; }

# --- удаление -----------------------------------------------------------------
if [ "${1:-}" = "--remove" ]; then
  for s in "${SKILLS[@]}"; do
    if [ -d "$DEST/$s" ]; then rm -rf "$DEST/$s"; say "убрала $s"; fi
  done
  say ""
  say "Готово. Навыки монтажа удалены. Остальное в Codex не тронуто."
  exit 0
fi

# --- проверки -----------------------------------------------------------------
command -v perl >/dev/null 2>&1 || die "нет perl. На маке он есть всегда; на линуксе поставьте пакет perl."

# Где лежат исходники: рядом со скриптом или надо склонировать
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/plugins/montazh"

if [ ! -d "$SRC/skills" ]; then
  command -v git >/dev/null 2>&1 || die "нет git, а рядом со скриптом нет папки plugins/montazh."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  say "Скачиваю навыки с гитхаба…"
  git clone --depth 1 --quiet https://github.com/LenaWhynot/whynot-skills.git "$TMP/repo"
  SRC="$TMP/repo/plugins/montazh"
fi

[ -d "$SRC/skills" ] || die "не нашла навыки в $SRC/skills"

# --- установка ----------------------------------------------------------------
mkdir -p "$DEST"

say "Кладу навыки в $DEST"
for s in first-run-setup video-clips-from-talk video-reel-from-process video-to-socials; do
  rm -rf "$DEST/$s"
  cp -R "$SRC/skills/$s" "$DEST/$s"
  say "  · $s"
done

# Монтажёр в Claude Code — субагент. В Codex субагентов нет, поэтому он
# становится обычным навыком-распределителем: у него подходящий frontmatter.
rm -rf "$DEST/montazher"
mkdir -p "$DEST/montazher"
cp "$SRC/agents/montazher.md" "$DEST/montazher/SKILL.md"
say "  · montazher (распределитель)"

# Пути к скриптам написаны под переменную Claude Code. В Codex её нет —
# переписываю на его собственную. Структура папок совпадает, меняется только корень.
FILES="$(grep -rl 'CLAUDE_PLUGIN_ROOT' "$DEST" 2>/dev/null || true)"
if [ -n "$FILES" ]; then
  printf '%s\n' "$FILES" | xargs perl -pi -e 's|\$\{CLAUDE_PLUGIN_ROOT\}/skills|\$\{CODEX_HOME:-\$HOME/\.codex\}/skills|g'
fi

LEFT="$(grep -rl 'CLAUDE_PLUGIN_ROOT' "$DEST" 2>/dev/null || true)"
[ -z "$LEFT" ] || die "часть путей не переписалась: $LEFT"

chmod +x "$DEST"/*/bin/*.sh 2>/dev/null || true

# --- что дальше ---------------------------------------------------------------
say ""
say "Готово. Поставлено пять навыков."
say ""
say "Теперь откройте НОВУЮ сессию Codex и скажите своими словами:"
say ""
say "    настрой монтажёра"
say ""
say "Мастер настройки сам скачает ffmpeg — без Homebrew и без пароля администратора,"
say "заведёт папки и прогонит весь путь на вашем же файле. Дальше говорите как хочется:"
say "«нарежь роликов из этой записи», «собери рилс из этой съёмки»."
say ""
say "Два предупреждения:"
say "  · В Codex есть свой навык transcribe от OpenAI. Если агент промахнулся мимо"
say "    монтажа, позовите нужный прямо: «нарежь роликов навыком video-clips-from-talk»."
say "  · Графику на каждую фразу этот набор не делает — это отдельный конвейер."
say ""
say "Убрать всё: bash install-codex.sh --remove"
