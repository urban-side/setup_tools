# setup_tools

新しく買ったMacの設定をするためのツールやコマンド群

## Makefile

```bash
make install
```

- 以下の表にあるもののうち `★` がついているものが設定、インストールされるはず
  - ダメなら画面から設定してください
  - 存在しない場合を除き、原則 HomeBrew からダウンロード
- Raycastのショートカットは設定しないので、手動で行うこと

## 各種アプリ・設定内容

### Macの設定

| 概要 | 設定内容 | 備考 |
|------|--------|------|
| ★Dock | デスクトップとDock -> Dockを自動的に表示/非表示 | |
| ディスプレイ | ディスプレイ設定 -> スペースを拡大 | |
| ポインタサイズ | 少し大きく・赤くする | |
| ★マウス加速 | CLIからマウス加速をOFFに設定 | [参考](https://www.teradas.jp/archives/36228/) |
| ★時刻表示 | 秒数まで表示する（`:` の点滅はOFF） | |
| ★バッテリーアイコン | バッテリーの％を表示 | |
| ★メニューバーアイコン | 必要に応じて幅を調節する（CLI） | [参考](https://zenn.dev/usagimaru/articles/9c4f45b0f3c906) |
| ☆Finder | ★拡張子を表示、設定 -> サイドバーから全ての項目を表示 | Raycast: `⌥ F` |
| ★Terminal | プロファイルの設定 | Raycast: `⌥ T`、設定ファイルあり |

### アプリ

| Tools | 備考 |
|-------|------|
| [Google Chrome](https://www.google.com/intl/ja_jp/chrome/) | Raycast: `⌥ G` |
| [Notion](https://www.notion.com/ja) | Raycast: `⌥ N` |
| [ChatGPT](https://openai.com/ja-JP/chatgpt/download/) | Raycast: `⌥ L` |
| [Rectangle Mac](https://rectangleapp.com/) | 設定ファイルあり |
| [scroll-reverser](https://pilotmoon.com/scrollreverser/) |  |
| [KeyboardCleanTool](https://folivora.ai/keyboardcleantool) |  |

### 開発系

| Tools | 備考 |
|-------|------|
| [Homebrew](https://brew.sh/ja/) | |
| [asdf](https://asdf-vm.com/) |  |
| [Warp](https://www.warp.dev/i) | GitHubでログイン |
| [Raycast](https://www.raycast.com/) | GitHubでログイン、`⌥ Space` に設定（Spotlightは `^ Space`） |
| [Visual Studio Code](https://code.visualstudio.com/) | GitHubでログイン、Raycast: `⌥ V` |
| [Cursor](https://www.cursor.com/ja) | GitHubでログイン、Raycast: `⌥ C` |
| [Docker](https://www.docker.com/products/docker-desktop/) | |
| [Postman](https://www.postman.com/) | Raycast: `⌥ ⌘ P` |
| [TablePlus](https://tableplus.com/) | Raycast: `⌥ ⌘ T` |
