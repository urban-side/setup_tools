#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "macOS の設定を適用します..."

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
open "${SCRIPT_DIR}/myprofile.terminal"
defaults write com.apple.Terminal "Startup Window Settings" -string "myprofile"
defaults write com.apple.Terminal "Default Window Settings" -string "myprofile"

# defaults は書いただけでは UI に反映されないため、ここでのみプロセスを再起動する
echo "🔁 変更を適用するためにシステムをリフレッシュします"
refresh_process Dock
refresh_process Finder
refresh_process SystemUIServer

echo "macOS の設定が完了しました！"
