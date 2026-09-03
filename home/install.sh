#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "ホームディレクトリの dotfiles を配置します..."

log "Gitの設定を適用します"
cp "${SCRIPT_DIR}/.gitconfig" ~/.gitconfig

log "zshのエイリアス設定を適用します"
cp "${SCRIPT_DIR}/.zsh_aliases" ~/.zsh_aliases
if grep -q '\.zsh_aliases' ~/.zshrc 2>/dev/null; then
  ok "~/.zshrc の読み込み設定は既に存在します"
else
  echo '[ -f ~/.zsh_aliases ] && source ~/.zsh_aliases' >> ~/.zshrc
  ok "~/.zshrc に読み込み設定を追加しました"
fi

echo "dotfiles の配置が完了しました！"
