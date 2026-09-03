#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "Claude Code / Codex の設定を適用します..."

mkdir -p ~/.claude
copy_if_changed "${SCRIPT_DIR}/CLAUDE.md" ~/.claude/CLAUDE.md "~/.claude/CLAUDE.md"
copy_if_changed "${SCRIPT_DIR}/AGENT.md"  ~/.claude/AGENT.md  "~/.claude/AGENT.md"

# リポジトリ側で消した Skill / hook を配置先からも消すため rsync --delete で同期する
sync_dir "${SCRIPT_DIR}/skills" ~/.claude/skills "~/.claude/skills"
sync_dir "${SCRIPT_DIR}/hooks"  ~/.claude/hooks  "~/.claude/hooks"
chmod +x ~/.claude/hooks/*.sh

# 規約の単一ソース化: Codex の AGENTS.md は Claude の AGENT.md への symlink にする
mkdir -p ~/.codex
if [ "$(readlink ~/.codex/AGENTS.md 2>/dev/null)" = "${HOME}/.claude/AGENT.md" ]; then
  skip "~/.codex/AGENTS.md の symlink は設定済みです"
else
  # 既存の実ファイル/ディレクトリは退避してから symlink を張る
  if [ ! -L ~/.codex/AGENTS.md ] && [ -e ~/.codex/AGENTS.md ]; then
    mv ~/.codex/AGENTS.md ~/.codex/AGENTS.md.bak
    warn "既存の ~/.codex/AGENTS.md を AGENTS.md.bak へ退避しました"
  fi
  ln -sfn ~/.claude/AGENT.md ~/.codex/AGENTS.md
  ok "~/.codex/AGENTS.md を ~/.claude/AGENT.md への symlink にしました"
fi

# hooks キーのみ上書きし、他の個人設定(permissions / enabledPlugins 等)は保持する
if [ ! -f ~/.claude/settings.json ]; then
  copy_if_changed "${SCRIPT_DIR}/settings.hooks.json" ~/.claude/settings.json "~/.claude/settings.json"
elif jq -e -s '.[0] * .[1] == .[0]' ~/.claude/settings.json "${SCRIPT_DIR}/settings.hooks.json" >/dev/null; then
  skip "~/.claude/settings.json の hooks 設定は最新です"
else
  jq -s '.[0] * .[1]' ~/.claude/settings.json "${SCRIPT_DIR}/settings.hooks.json" > ~/.claude/settings.json.tmp \
    && mv ~/.claude/settings.json.tmp ~/.claude/settings.json
  ok "~/.claude/settings.json に hooks 設定をマージしました"
fi

echo "Claude Code の設定が完了しました！"
