#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "アプリと開発ツールをインストールします..."

if command -v brew &>/dev/null; then
  ok "Homebrewは既にインストールされています"
else
  log "Homebrewをインストールします..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Homebrewのパスを通す
  if [[ "$(uname -m)" == "arm64" ]]; then
    brew_prefix="/opt/homebrew"
  else
    brew_prefix="/usr/local"
  fi
  append_line_once ~/.zprofile "eval \"\$(${brew_prefix}/bin/brew shellenv)\"" "~/.zprofile の Homebrew パス"
  eval "$("${brew_prefix}/bin/brew" shellenv)"
fi

log "Homebrewをアップデートします..."
brew update

# Brewfile が唯一のアプリ一覧。--cleanup は付けないので、Brewfile から
# 消しただけでは環境からアンインストールされない(意図的)。
log "Brewfile の内容を適用します..."
brew bundle --file "${SCRIPT_DIR}/Brewfile" --no-upgrade

append_line_once ~/.zshrc 'eval "$(mise activate zsh)"' "~/.zshrc の mise 有効化"

echo "すべてのアプリと開発ツールのインストールが完了しました！"
