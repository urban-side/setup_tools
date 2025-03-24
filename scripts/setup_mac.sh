#!/bin/bash

echo "Macの設定を適用します..."

echo "🚀 Dockを自動的に表示/非表示に設定します"
defaults write com.apple.dock autohide -bool true

echo "🚀 マウス加速をOFFに設定します"
defaults write .GlobalPreferences com.apple.mouse.scaling -1

echo "🚀 時刻表示を秒数まで表示するように設定します"
defaults write com.apple.menuextra.clock ShowSeconds -bool true
defaults write com.apple.menuextra.clock FlashDateSeparators -bool false

echo "🚀 バッテリーの%表示を有効化します"
defaults write com.apple.menuextra.battery ShowPercent -string "YES"

echo "🚀 メニューバーアイコンの幅を調節します"
defaults write -globalDomain NSStatusItemSpacing -int 12
defaults write -globalDomain NSStatusItemSelectionPadding -int 8

echo "🚀 Finderでは拡張子を表示するように設定します"
defaults write com.apple.finder ShowExtension -bool true

echo "🚀 Terminalプロファイルを設定します"
open ./config/myprofile.terminal
defaults write com.apple.Terminal "Startup Window Settings" -string "myprofile"
defaults write com.apple.Terminal "Default Window Settings" -string "myprofile"

echo "🔁 変更を適用するためにシステムをリフレッシュします"
killall Dock
killall Finder
killall SystemUIServer
killall Terminal

echo "Macの設定が完了しました！"
