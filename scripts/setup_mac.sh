#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "Macの設定を適用します..."

log "Dockを自動的に表示/非表示に設定します"
defaults write com.apple.dock autohide -bool true

log "マウス加速をOFFに設定します"
defaults write .GlobalPreferences com.apple.mouse.scaling -1

log "時刻表示を秒数まで表示するように設定します"
defaults write com.apple.menuextra.clock ShowSeconds -bool true
defaults write com.apple.menuextra.clock FlashDateSeparators -bool false

log "バッテリーの%表示を有効化します"
defaults write com.apple.menuextra.battery ShowPercent -string "YES"

log "メニューバーアイコンの幅を調節します"
defaults write -globalDomain NSStatusItemSpacing -int 12
defaults write -globalDomain NSStatusItemSelectionPadding -int 8

log "Finderでは拡張子を表示するように設定します"
defaults write com.apple.finder ShowExtension -bool true

log "Terminalプロファイルを設定します"
open "${REPO_ROOT}/macos/myprofile.terminal"
defaults write com.apple.Terminal "Startup Window Settings" -string "myprofile"
defaults write com.apple.Terminal "Default Window Settings" -string "myprofile"

log "Gitの設定を適用します"
cp "${REPO_ROOT}/home/.gitconfig" ~/.gitconfig

log "zshのエイリアス設定を適用します"
cp "${REPO_ROOT}/home/.zsh_aliases" ~/.zsh_aliases
if ! grep -q '\.zsh_aliases' ~/.zshrc 2>/dev/null; then
  echo '[ -f ~/.zsh_aliases ] && source ~/.zsh_aliases' >> ~/.zshrc
fi

log "Claude Codeの設定(CLAUDE.md / skills / hooks)を適用します"
mkdir -p ~/.claude/skills ~/.claude/hooks
cp "${REPO_ROOT}/claude/CLAUDE.md" ~/.claude/CLAUDE.md
cp "${REPO_ROOT}/claude/AGENT.md" ~/.claude/AGENT.md
cp -R "${REPO_ROOT}/claude/skills/" ~/.claude/skills/
cp "${REPO_ROOT}"/claude/hooks/*.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.sh

log "Codex の AGENTS.md を Claude の AGENT.md への symlink にします(規約の単一ソース化)"
mkdir -p ~/.codex
# 既存の実ファイル/ディレクトリは退避してから symlink を張る(再実行時は symlink なので素通り)
if [ ! -L ~/.codex/AGENTS.md ] && [ -e ~/.codex/AGENTS.md ]; then
  mv ~/.codex/AGENTS.md ~/.codex/AGENTS.md.bak
fi
ln -sfn ~/.claude/AGENT.md ~/.codex/AGENTS.md

# settings.json に hooks 設定をマージ(hooks キーのみ上書き、他の個人設定は保持)
if [ -f ~/.claude/settings.json ]; then
  jq -s '.[0] * .[1]' ~/.claude/settings.json "${REPO_ROOT}/claude/settings.hooks.json" > ~/.claude/settings.json.tmp \
    && mv ~/.claude/settings.json.tmp ~/.claude/settings.json
else
  cp "${REPO_ROOT}/claude/settings.hooks.json" ~/.claude/settings.json
fi

echo "🔁 変更を適用するためにシステムをリフレッシュします"
refresh_process Dock
refresh_process Finder
refresh_process SystemUIServer

echo "Macの設定が完了しました！"
