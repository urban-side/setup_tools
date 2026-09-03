.PHONY: install macos home claude apps

## 全部入り
install:
	bash ./setup.sh

## macOS の defaults と Terminal プロファイル
macos:
	bash ./macos/install.sh

## ~/ 直下の dotfiles
home:
	bash ./home/install.sh

## Claude Code / Codex の設定
claude:
	bash ./claude/install.sh

## Homebrew でアプリと開発ツール
apps:
	bash ./apps/install.sh
