# setup_tools

新しく買った Mac の設定をするためのツールとコマンド群。

## セットアップ

```sh
make install     # 全部入り
```

個別に流すこともできる。ディレクトリと 1:1 で対応している。

| コマンド | 内容 | 対象 |
| --- | --- | --- |
| `make macos` | macOS の `defaults` と Terminal プロファイル | `macos/` |
| `make home` | `~/` 直下の dotfiles | `home/` |
| `make claude` | Claude Code / Codex の設定 | `claude/` |
| `make apps` | Homebrew でアプリと開発ツール | `apps/` |

> [!WARNING]
> 既に `~/.claude/` を使い込んでいるマシンでは `make claude`（および `make install`）を実行しないこと。リポジトリ側はサニタイズ版のため、ローカルの Skill が上書きされる。詳細は [claude/README.md](./claude/README.md)。

## 構成

```
setup_tools/
├── lib/common.sh   … 各 install.sh が source する共通ヘルパ
├── home/           … ~/ 直下へ置くもの
├── claude/         … ~/.claude/ へ置くもの（サニタイズ版）
├── macos/          … defaults と Terminal プロファイル
├── apps/           … Homebrew（Brewfile が唯一のアプリ一覧）
└── manual/         … 手動でインポートするもの（スクリプトは触らない）
```

配置先でディレクトリを分けている。何かを追加するときは「どこに置かれるか」で置き場所が決まる。

各 `install.sh` は冪等で、2 回目以降は変更があったものだけを適用する。

## Mac の設定

`★` が `make macos` で自動設定されるもの。それ以外は画面から手動で設定する。

| 概要 | 設定内容 | 備考 |
| --- | --- | --- |
| ★Dock | デスクトップと Dock → Dock を自動的に表示/非表示 | |
| ディスプレイ | ディスプレイ設定 → スペースを拡大 | |
| ポインタサイズ | 少し大きく・赤くする | |
| ★マウス加速 | CLI からマウス加速を OFF に設定 | [参考](https://www.teradas.jp/archives/36228/) |
| ★時刻表示 | 秒数まで表示する（`:` の点滅は OFF） | |
| ★バッテリーアイコン | バッテリーの % を表示 | |
| ★メニューバーアイコン | 必要に応じて幅を調節する | [参考](https://zenn.dev/usagimaru/articles/9c4f45b0f3c906) |
| Finder | ★拡張子を表示 / 設定 → サイドバーから全ての項目を表示 | Raycast: `⌥ F` |
| ★Terminal | プロファイルの設定 | Raycast: `⌥ T` |

`make claude` で `~/.claude/`（`CLAUDE.md` / `AGENT.md` / `skills` / `hooks`）と `~/.codex/AGENTS.md` が配置される。

## アプリ

インストール対象の一覧は [apps/Brewfile](./apps/Brewfile) が唯一の情報源。下表は補足（ショートカットとログイン方法）だけを持つ。

| ツール | 備考 |
| --- | --- |
| [Google Chrome](https://www.google.com/intl/ja_jp/chrome/) | Raycast: `⌥ G` |
| [Notion](https://www.notion.com/ja) | Raycast: `⌥ N` |
| [ChatGPT](https://openai.com/ja-JP/chatgpt/download/) | Raycast: `⌥ L` |
| [Rectangle](https://rectangleapp.com/) | 設定ファイルあり → [manual/](./manual/README.md) |
| [scroll-reverser](https://pilotmoon.com/scrollreverser/) | |
| [KeyboardCleanTool](https://folivora.ai/keyboardcleantool) | |
| [Homebrew](https://brew.sh/ja/) | 未導入なら `make apps` が入れる |
| [mise](https://mise.jdx.dev/) | バージョン管理 |
| [Warp](https://www.warp.dev/i) | GitHub でログイン |
| [Raycast](https://www.raycast.com/) | GitHub でログイン、`⌥ Space` に設定（Spotlight は `^ Space`）。設定ファイルあり → [manual/](./manual/README.md) |
| [Visual Studio Code](https://code.visualstudio.com/) | GitHub でログイン、Raycast: `⌥ V` |
| [Cursor](https://www.cursor.com/ja) | GitHub でログイン、Raycast: `⌥ C` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | |
| [Postman](https://www.postman.com/) | Raycast: `⌥ ⌘ P` |
| [TablePlus](https://tableplus.com/) | Raycast: `⌥ ⌘ T` |

手動でインストール済みのアプリは `cask_args adopt: true` により Homebrew の管理下へ取り込まれる。

`brew bundle` に `--cleanup` は付けていないので、Brewfile から行を消しても環境からアンインストールはされない。

## 手動で入れるもの

Rectangle と Raycast の設定は自動適用していない。手順は [manual/README.md](./manual/README.md) を参照。
