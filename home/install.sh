#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "ホームディレクトリの dotfiles を配置します..."

copy_if_changed "${SCRIPT_DIR}/.gitconfig"    ~/.gitconfig    "~/.gitconfig"
copy_if_changed "${SCRIPT_DIR}/.zsh_aliases"  ~/.zsh_aliases  "~/.zsh_aliases"
append_line_once ~/.zshrc '[ -f ~/.zsh_aliases ] && source ~/.zsh_aliases' "~/.zshrc のエイリアス読み込み"

echo "dotfiles の配置が完了しました！"
