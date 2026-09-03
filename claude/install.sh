#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "Claude Code / Codex の設定を適用します..."

log "CLAUDE.md / AGENT.md / skills / hooks を配置します"
mkdir -p ~/.claude/skills ~/.claude/hooks
cp "${SCRIPT_DIR}/CLAUDE.md" ~/.claude/CLAUDE.md
cp "${SCRIPT_DIR}/AGENT.md" ~/.claude/AGENT.md
cp -R "${SCRIPT_DIR}/skills/" ~/.claude/skills/
cp "${SCRIPT_DIR}"/hooks/*.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh

log "Codex の AGENTS.md を Claude の AGENT.md への symlink にします(規約の単一ソース化)"
mkdir -p ~/.codex
# 既存の実ファイル/ディレクトリは退避してから symlink を張る(再実行時は symlink なので素通り)
if [ ! -L ~/.codex/AGENTS.md ] && [ -e ~/.codex/AGENTS.md ]; then
  mv ~/.codex/AGENTS.md ~/.codex/AGENTS.md.bak
  warn "既存の ~/.codex/AGENTS.md を AGENTS.md.bak へ退避しました"
fi
ln -sfn ~/.claude/AGENT.md ~/.codex/AGENTS.md

log "settings.json に hooks 設定をマージします"
# hooks キーのみ上書きし、他の個人設定(permissions / enabledPlugins 等)は保持する
if [ -f ~/.claude/settings.json ]; then
  jq -s '.[0] * .[1]' ~/.claude/settings.json "${SCRIPT_DIR}/settings.hooks.json" > ~/.claude/settings.json.tmp \
    && mv ~/.claude/settings.json.tmp ~/.claude/settings.json
else
  cp "${SCRIPT_DIR}/settings.hooks.json" ~/.claude/settings.json
fi

echo "Claude Code の設定が完了しました！"
