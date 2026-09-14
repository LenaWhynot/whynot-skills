#!/usr/bin/env bash
# Установка навыков монтажа в Codex.
#
# В Claude Code этот набор ставится плагином. Codex плагины Claude Code не читает,
# зато читает навыки из своей папки skills — этот скрипт их туда и кладёт,
# заодно переписывая пути под переменные Codex.
#
# Запуск:  bash install-codex.sh                 — оба набора
#          bash install-codex.sh --montazh        — только монтаж
#          bash install-codex.sh --content        — только контент-цех
# Снести:  bash install-codex.sh --remove

set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST="$CODEX_HOME/skills"

# набор → навыки плагина + его агент, который в Codex становится навыком-распределителем
MONTAZH_SKILLS=(first-run-setup video-clips-from-talk video-reel-from-process video-to-socials)
MONTAZH_AGENT="montazher"
CONTENT_SKILLS=(themes-from-questions series-plan first-screen-brief on-screen-text decode-reference)
CONTENT_AGENT="tsekh"

SKILLS=("${MONTAZH_SKILLS[@]}" "$MONTAZH_AGENT" "${CONTENT_SKILLS[@]}" "$CONTENT_AGENT")

WANT_MONTAZH=1; WANT_CONTENT=1
case "${1:-}" in
  --montazh) WANT_CONTENT=0 ;;
  --content) WANT_MONTAZH=0 ;;
esac

say() { printf '%s\n' "$*"; }
die() { printf 'Не получилось: %s\n' "$*" >&2; exit 1; }

# --- удаление -----------------------------------------------------------------
if [ "${1:-}" = "--remove" ]; then
  for s in "${SKILLS[@]}"; do
    if [ -d "$DEST/$s" ]; then rm -rf "$DEST/$s"; say "убрала $s"; fi
  done
  say ""
  say "Готово. Навыки из этого набора удалены. Остальное в Codex не тронуто."
  exit 0
fi

# --- проверки -----------------------------------------------------------------
command -v perl >/dev/null 2>&1 || die "нет perl. На маке он есть всегда; на линуксе поставьте пакет perl."

# Где лежат исходники: рядом со скриптом или надо склонировать
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE"

if [ ! -d "$ROOT/plugins/montazh/skills" ]; then
  command -v git >/dev/null 2>&1 || die "нет git, а рядом со скриптом нет папки plugins/."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  say "Скачиваю навыки с гитхаба…"
  git clone --depth 1 --quiet https://github.com/LenaWhynot/whynot-skills.git "$TMP/repo"
  ROOT="$TMP/repo"
fi

[ -d "$ROOT/plugins/montazh/skills" ] || die "не нашла навыки в $ROOT/plugins"

# --- установка ----------------------------------------------------------------
mkdir -p "$DEST"
say "Кладу навыки в $DEST"

put_skills() {           # put_skills <папка плагина> <навык>...
  local plug="$1"; shift
  local s
  for s in "$@"; do
    [ -d "$ROOT/plugins/$plug/skills/$s" ] || die "нет навыка $s в плагине $plug"
    rm -rf "$DEST/$s"
    cp -R "$ROOT/plugins/$plug/skills/$s" "$DEST/$s"
    say "  · $s"
  done
}

# Агент плагина в Claude Code — субагент. В Codex субагентов нет, поэтому он
# становится обычным навыком-распределителем: у него подходящий frontmatter.
put_agent() {            # put_agent <папка плагина> <имя агента>
  local plug="$1" a="$2"
  [ -f "$ROOT/plugins/$plug/agents/$a.md" ] || die "нет агента $a в плагине $plug"
  rm -rf "$DEST/$a"; mkdir -p "$DEST/$a"
  cp "$ROOT/plugins/$plug/agents/$a.md" "$DEST/$a/SKILL.md"
  say "  · $a (распределитель)"
}

if [ "$WANT_MONTAZH" = 1 ]; then
  say " монтаж:"
  put_skills montazh "${MONTAZH_SKILLS[@]}"
  put_agent  montazh "$MONTAZH_AGENT"
fi

if [ "$WANT_CONTENT" = 1 ]; then
  say " контент-цех:"
  put_skills content-tseh "${CONTENT_SKILLS[@]}"
  put_agent  content-tseh "$CONTENT_AGENT"
fi

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
say "Готово. Теперь откройте НОВУЮ сессию Codex и скажите своими словами:"
say ""
if [ "$WANT_MONTAZH" = 1 ]; then
  say "    настрой монтажёра"
  say ""
  say "Мастер настройки сам скачает ffmpeg — без Homebrew и без пароля администратора,"
  say "заведёт папки и прогонит весь путь на вашем же файле. Дальше говорите как хочется:"
  say "«нарежь роликов из этой записи», «собери рилс из этой съёмки»."
  say ""
fi
if [ "$WANT_CONTENT" = 1 ]; then
  say "    о чём мне писать, вот комментарии под последним постом"
  say ""
  say "Так же своими словами: «нужна серия к запуску», «сделай обложку для этого видео»,"
  say "«вот ссылка, разбери и скажи, что забрать»."
  say ""
fi
say "Два предупреждения:"
say "  · В Codex есть свой навык transcribe от OpenAI. Если агент промахнулся мимо"
say "    монтажа, позовите нужный прямо: «нарежь роликов навыком video-clips-from-talk»."
say "  · Контент-цех не пишет текст вместо вас — вашего голоса в наборе нет."
say ""
say "Поставить только одно: bash install-codex.sh --montazh  (или --content)"
say "Убрать всё:            bash install-codex.sh --remove"
