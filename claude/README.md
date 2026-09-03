# claude/ — Claude Code / Codex の設定

`claude/install.sh`（= `make claude`）で `~/.claude/` と `~/.codex/AGENTS.md` へ配置される。

## ⚠️ ここに置いてあるのはサニタイズ版

`skills/` 配下は、ローカルの `~/.claude/skills/` から**社内固有の情報を置換したうえで**同期している。本リポジトリは公開リポジトリなので、実チケット ID・社内リポジトリ名・実企業名・ベンダー名などをそのまま置くことはできない。

置換の例:

| ローカル | このリポジトリ |
| --- | --- |
| 実際の Jira プロジェクトキー（`ABCD-1234`） | `PROJ-1234` |
| 社内リポジトリ名 | 一般化した表現 |
| 実企業名・実テナント名 | `拠点A` 等 |
| 外部ベンダーの製品名 | 「IVR 事業者」等の役割名 |

このため **`~/.claude/skills/` と `claude/skills/` に diff があるのは正常**で、同期漏れではない。

## 同期の向き

| 向き | 手段 | 使う場面 |
| --- | --- | --- |
| リポジトリ → ローカル | `make claude` | **新しいマシンのセットアップ時** |
| ローカル → リポジトリ | 手動でサニタイズしてコミット | ローカルで設定を更新したとき |

### 既にローカルが正のマシンでは `make claude` を実行しない

`claude/install.sh` は `rsync --delete` で `~/.claude/skills/` を同期する。ローカルに実データ版の Skill が入っているマシンでこれを実行すると、**サニタイズ版で上書きされる**。

`make install`（全部入り）にも `claude` は含まれるので、既存マシンで設定を入れ直したいときは `make macos` / `make home` / `make apps` を個別に叩くこと。

## settings.json の扱い

`settings.hooks.json` は `hooks` キーだけを持つ断片で、`jq -s '.[0] * .[1]'` で `~/.claude/settings.json` へマージされる。`permissions` や `enabledPlugins` といった個人設定・マシン固有設定はリポジトリで管理せず、マージ時も保持される。

## 規約の単一ソース化

`~/.codex/AGENTS.md` は `~/.claude/AGENT.md` への symlink になる。Claude Code と Codex で規約を二重管理しないため。
