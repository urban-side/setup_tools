#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

echo "macOS の設定を適用します..."

# 修飾キー + Space のショートカットを設定する。id は com.apple.symbolichotkeys の番号、
# 修飾キーは ^=262144 / ⌥=524288 / ⌘=1048576(32 と 49 は Space の文字コードとキーコード)
set_space_hotkey() {
  local id="$1" modifiers="$2"
  defaults write com.apple.symbolichotkeys AppleSymbolicHotKeys -dict-add "$id" \
    "<dict><key>enabled</key><true/><key>value</key><dict><key>type</key><string>standard</string><key>parameters</key><array><integer>32</integer><integer>49</integer><integer>${modifiers}</integer></array></dict></dict>"
}

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

log "入力ソースの切り替えを ⌘ Space に設定します"
set_space_hotkey 60 1048576

log "Spotlight検索を ^ Space に設定します"
set_space_hotkey 64 262144

log "Raycastの起動キーを ⌥ Space に設定します"
defaults write com.raycast.macos raycastGlobalHotkey -string "Option-49"

log "Terminalプロファイルを設定します"
open "${SCRIPT_DIR}/myprofile.terminal"
defaults write com.apple.Terminal "Startup Window Settings" -string "myprofile"
defaults write com.apple.Terminal "Default Window Settings" -string "myprofile"

# defaults は書いただけでは UI に反映されないため、ここでのみプロセスを再起動する
echo "🔁 変更を適用するためにシステムをリフレッシュします"
refresh_process Dock
refresh_process Finder
refresh_process SystemUIServer
# キーボードショートカットは再起動ではなくこれで読み直させる
/System/Library/PrivateFrameworks/SystemAdministration.framework/Resources/activateSettings -u \
  || warn "ショートカットの変更はログインし直すと反映されます"

echo "macOS の設定が完了しました！"
