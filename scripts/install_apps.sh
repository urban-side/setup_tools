#!/bin/bash

echo "🚀 アプリのインストールを開始します..."

# Homebrewがインストールされているか確認
if ! command -v brew &> /dev/null; then
  echo "Homebrewをインストールします..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Homebrewのパスを通す
  if [[ $(uname -m) == "arm64" ]]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
  else
    echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/usr/local/bin/brew shellenv)"
  fi
else
  echo "✅ Homebrewは既にインストールされています"
fi

# Homebrewをアップデート
echo "Homebrewをアップデートします..."
brew update

# インストールするアプリケーションのリスト (Casks)
echo "🍺 アプリケーションをインストールします..."
cask_apps=(
  "google-chrome"
  "notion"
  "chatgpt"
  "rectangle"
  "scroll-reverser"
  "keyboardcleantool"
)

# Caskアプリをインストール
for app in "${cask_apps[@]}"; do
  if brew list --cask "$app" &>/dev/null; then
    echo "✅ $app は既にインストールされています"
  else
    echo "🔄 $app をインストールしています..."
    brew install --cask "$app"
  fi
done

# 開発ツールをインストール
echo "🛠 開発ツールをインストールします..."
dev_tools=(
  "asdf"
  "warp"
  "raycast"
  "visual-studio-code"
  "cursor"
  "docker"
  "postman"
  "tableplus"
)

# 開発ツールをインストール
for tool in "${dev_tools[@]}"; do
  if brew list "$tool" &>/dev/null; then
    echo "✅ $tool は既にインストールされています"
  else
    echo "🔄 $tool をインストールしています..."
    brew install "$tool"
  fi
done

echo "🎉 すべてのアプリと開発ツールのインストールが完了しました！"
