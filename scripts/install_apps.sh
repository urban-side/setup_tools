#!/bin/bash
set -euo pipefail

echo "🚀 アプリのインストールを開始します..."

# Homebrewがインストールされているか確認
if ! command -v brew &>/dev/null; then
  echo "Homebrewをインストールします..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Homebrewのパスを通す
  if [[ $(uname -m) == "arm64" ]]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >>~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
  else
    echo 'eval "$(/usr/local/bin/brew shellenv)"' >>~/.zprofile
    eval "$(/usr/local/bin/brew shellenv)"
  fi
else
  echo "✅ Homebrewは既にインストールされています"
fi

install_formula_if_missing() {
  local formula="$1"
  if brew list --formula "$formula" &>/dev/null; then
    echo "✅ ${formula} は既にインストールされています"
  else
    echo "🔄 ${formula} をインストールしています..."
    brew install "$formula"
  fi
}

install_cask_if_missing() {
  local cask="$1"
  if brew list --cask "$cask" &>/dev/null; then
    echo "✅ ${cask} は既にインストールされています"
  else
    echo "🔄 ${cask} をインストールしています..."
    local output=""
    local status=0
    set +e
    output="$(brew install --cask "$cask" 2>&1)"
    status=$?
    set -e

    if [[ "$status" -eq 0 ]]; then
      echo "$output"
      return 0
    fi

    # Homebrew管理外でも /Applications に既存アプリがある場合はスキップ扱いにする
    if echo "$output" | grep -Eq "already an App at|already installed"; then
      echo "⚠️ ${cask} は既存アプリを検出したためスキップします"
      return 0
    fi

    echo "$output"
    return "$status"
  fi
}

ensure_mise_activation() {
  local shell_rc="${HOME}/.zshrc"
  local activation_line='eval "$(mise activate zsh)"'
  if [[ ! -f "$shell_rc" ]]; then
    touch "$shell_rc"
  fi
  if grep -Fqx "$activation_line" "$shell_rc"; then
    echo "✅ zsh の mise 有効化設定は既に存在します"
  else
    echo "$activation_line" >>"$shell_rc"
    echo "✅ zsh に mise の有効化設定を追加しました"
  fi
}

# Homebrewをアップデート
echo "Homebrewをアップデートします..."
brew update

# アプリケーションをインストール
echo "🍺 アプリケーションをインストールします..."
cask_apps=(
  "google-chrome"
  "notion"
  "chatgpt"
  "rectangle"
  "scroll-reverser"
  "keyboardcleantool"
)
for app in "${cask_apps[@]}"; do
  install_cask_if_missing "$app"
done

# 開発ツールをインストール
echo "🛠 開発ツールをインストールします..."
dev_formulas=(
  "mise"
)
for tool in "${dev_formulas[@]}"; do
  install_formula_if_missing "$tool"
done

dev_casks=(
  "warp"
  "raycast"
  "visual-studio-code"
  "cursor"
  "docker"
  "postman"
  "tableplus"
)
for tool in "${dev_casks[@]}"; do
  install_cask_if_missing "$tool"
done

ensure_mise_activation

echo "🎉 すべてのアプリと開発ツールのインストールが完了しました！"
