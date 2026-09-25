---
name: create-pr
description: |
  ブランチ作成〜PR 作成を K の規約(ブランチ命名 / PR タイトル形式 / PR テンプレート準拠)どおりに行う。
  トリガー: "PR作成", "PR作って", "プルリク", "pull request", "gh pr create", "ブランチ切って", "pushしてPR"
  使用場面: (1) 新規ブランチの作成、(2) PR の新規作成、(3) 既存 PR のタイトル・本文の修正
---

# create-pr

ブランチ作成と PR 作成を規約どおりに行うスキル。Git/PR 規約(ブランチ命名・PR タイトル・テンプレート準拠)の正は本スキル(AGENT.md §5 から参照される)。
チケット管理は Linear(旧 Jira は参照のみ)。
チケット運用のないリポジトリ(個人 repo 等)では、チケット ID 前提の命名・タイトル形式よりリポジトリの慣習を優先する(AGENT.md §5「リポジトリの慣習が正」)。

## 手順

### 1. ticket ID の特定

- ユーザー指示・プロジェクトメモリ・作業中チケットから Linear の Issue ID（例: `TEAM-1234`）を特定する。Linear MCP で実在とステータスを確認する。
- 移行前の Jira キーしか分からない場合は、Linear で旧キーを検索して Issue ID に読み替える。
- 特定できない場合は推測せず K に確認する。

### 2. ブランチ命名

- 原則 `topic/<ticket ID>` または `feat/<ticket ID>`。ブランチ名・タイトルに Issue ID が入っていれば Linear の GitHub 連携が PR を自動で紐付ける。
  - `topic/<ID>`: 統合ブランチ。複数 PR をスタックする開発の基点（topic → main）。
  - `feat/<ID>`: 個別実装ブランチ。単発ならそのまま、スタック開発では topic にぶら下げる。
  - 派生が複数要る場合は `feat/<ID>-<短いsuffix>` （例: `feat/TEAM-1234-user-seed`）。
  - 移行前の Jira キーで切ったブランチ・PR は改名しない。Linear へは Issue の links に PR URL を手で足して紐付ける。

### 2.5 ベースブランチ（リポジトリごとに違う・必須確認）

- `gh pr create --base` を決める前に、そのリポジトリの直近のマージ済み PR の向きを `gh pr list --state merged --limit 10 --json baseRefName,headRefName` で確認する。
- `main <- staging` のようにリリース用ブランチを挟む運用のリポジトリでは、実装 PR は `staging <- feat/...` で作り、枝も `origin/staging` から切る。

### 3. PR テンプレートの読込（必須・スキップ禁止）

- `gh pr create` の**前に** `.github/pull_request_template.md` と `.github/PULL_REQUEST_TEMPLATE/` ディレクトリを必ず読む。
- テンプレートが存在する場合、本文はテンプレートの全セクション構成に従う。独自セクションを追加せず、書きたい内容（動作確認の curl 結果等）はテンプレートの該当節の中に収める。
- テンプレートに監査目的のセクション（AI 利用申告・コンティンジェンシープラン等）がある場合、省略不可。
- テンプレートのチケット欄には Linear Issue の URL を入れる。

### 4. PR タイトル

- `[<ticket ID>]タイトル`（例: `[TEAM-1234]○○を修正`）。
- 統合 PR（topic → main）では `[TOPIC]タイトル` の実績あり。

### 5. （任意・既定スキップ）PR 作成前の codex セカンドオピニオン

- 既定は実行しない。K が求めたとき、または差分が大きい・本番影響がある変更のときに**実行を提案する**（勝手に必須化しない）。
- 実行する場合は codex Skill の③構造化レビュー（`codex exec` + review-schema.json）を使い、裏取りループで confirmed になった指摘のみ修正してから PR を作成する。opinion は PR 本文に書かず K への報告に回す。

### 6. 作成と報告

- 作成後、対応する Linear Issue のステータスを PR の状態に合わせる（draft=進行中 / ready=レビュー中）。

- draft / ready はユーザー指示に従う。指示がなければ draft で作成。
- 完了報告では、テンプレートの各セクションを埋めたことと PR URL を示し、K の元指示との対応を突合せる。

## 由来

同種の差戻し（テンプレート無視・命名規約違反）を複数回受けたことから、収集→Skill 化ライフサイクルの第 1 号としてスキル化。
