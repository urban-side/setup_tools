# manual/ — 手動で適用する設定

ここにあるファイルは**どのスクリプトからも適用されない**。`make install` を流しても反映されないので、必要なときに下記の手順で手動インポートすること。

バックアップとして置いてあるので、消さずに更新だけしていく想定。

## RectangleConfig.json

ウィンドウ配置ツール [Rectangle](https://rectangleapp.com/) の設定。

1. Rectangle を起動する（未インストールなら `make apps` で入る）
2. メニューバーの Rectangle アイコン → `Settings...`
3. 歯車アイコン → `Import Settings...`
4. `manual/RectangleConfig.json` を選ぶ

エクスポートは同じメニューの `Export Settings...`。設定を変えたらここへ上書きしてコミットする。

## Raycast/*.rayconfig

[Raycast](https://www.raycast.com/) の設定。**マシンごとに 1 ファイル**あり、ファイル名で用途を分けている。

| ファイル | 用途 |
| --- | --- |
| `Raycast 2026-01-28 19.08.21_buysell_macbookpro.rayconfig` | 業務用 MacBook Pro |
| `Raycast 2026-03-08 21.48.35_private_macbookair.rayconfig` | 私用 MacBook Air |

1. Raycast を起動する（未インストールなら `make apps` で入る）
2. `⌘ ,` で Settings → `Advanced`
3. `Import / Export` → `Import` からファイルを選ぶ

エクスポートは同じ画面の `Export`。インポート時にパスワードを求められる場合がある。

**ショートカットの割り当ては自動化していない。** Raycast 自体の起動キー（`⌥ Space`）を含め、README のショートカット表を見ながら手で設定すること。
