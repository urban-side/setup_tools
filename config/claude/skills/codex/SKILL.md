---
name: codex
description: |
  Codex CLI（OpenAI, gpt-5.6-sol）に相談・検算・書込作業を委譲する。公式 plugin(openai-codex)と役割分担: 読み取りレビューは公式コマンド/K操作、書込委譲は codex-rescue subagent、構造化レビュー(裏取りループ付き)は本Skill固有。
  トリガー: "codex", "codexと相談", "codexに聞いて", "codex review", "コードレビュー", "レビューして", "セカンドオピニオン", "構造化レビュー", "codexに任せて", "codexに調査させて"
  使用場面: (1) 文言・設計の相談、(2) PR前の構造化セカンドオピニオン(裏取り前提)、(3) 明確仕様のバルク作業・調査の委譲
---

# Codex

Codex CLI(0.144.5 / 0.145.0 で検証)を Claude Code のサブとして使うスキル。Claude×Codex の振り分け基準は本 Skill §2 が正(AGENT.md §6 は一般原則のみ)。

**2026-08-03 に公式 plugin `codex@openai-codex`(openai/codex-plugin-cc)を導入し、役割分担した。全用途を本 Skill で賄わない。**

## §0 公式 plugin との役割分担(まずここで判断)

| 用途 | 担当 | 呼び方 |
|---|---|---|
| 読み取りレビュー(非ステアラブル) | **公式 plugin** | K が `/codex:review [--base <branch>] [--background]` を実行(Claude からは起動不可・スラッシュコマンドは人間操作) |
| 読み取りレビュー(観点指定・設計を疑う) | **公式 plugin** | K が `/codex:adversarial-review [--base <branch>] <観点>` を実行 |
| 書込委譲(調査・修正・バルク作業) | **公式 plugin の subagent** | Claude が自律的に `Agent(subagent_type: "codex:codex-rescue", prompt: "<仕様>")` を呼ぶ。K の指示を待たず、Claude が「Codex に投げるべき」と判断した時点で使ってよい(subagent 定義が proactive use を許可) |
| セッション引継(Claude↔Codex) | **公式 plugin** | K が `/codex:transfer` を実行 |
| **構造化レビュー(裏取りループ前提)** | **本 Skill** | `codex exec --output-schema review-schema.json`(下記§1③)。公式 schema には `evidence`/`verify_hint` が無く裏取りに不向きなため独自維持 |
| 自由形式の相談(レビュー枠に収まらない壁打ち) | **本 Skill** | `codex exec`(下記§1①) |

公式 plugin 側の内部規律(`codex-result-handling` skill)は「レビュー結果を出したら **必ず停止し、直す前に K に確認**。自動適用は禁止」と定めており、本 Skill の §4 裏取りループと同じ思想。公式コマンドを使う場合も裏取りを省略しない。

書込委譲(`codex:codex-rescue`)は既定で **write-capable**(sandbox=workspace-write 相当)。モデル未指定時は `~/.codex/config.toml` の `model = "gpt-5.6-sol"` が使われる(K指示のモデルピンは既にグローバル設定で担保済み。上位モデル登場時はそちらを更新する)。**旧 `~/.codex/writer.config.toml` / `--profile writer` 方式は廃止**(公式 subagent に一本化)。

## §1 本 Skill が担当する用途

| 用途 | コマンド | 使いどころ |
|---|---|---|
| ①汎用相談 | `codex exec --sandbox read-only --cd <dir> -o /tmp/codex-last.md "<request>"` | 文言検討・設計相談・バグ調査・アーキ分析(レビュー枠に収まらない自由形式) |
| ③構造化レビュー | `codex exec --sandbox read-only --cd <repo> --output-schema ~/.claude/skills/codex/review-schema.json -o /tmp/codex-last.json "git diff <範囲> で差分を確認しコードレビューしてください。観点: <観点>。<定型末尾指示>"` | **PR 前の本命**。findings を JSON で受け、§4 の裏取りループを回す |

注意(0.144.5 実測):
- `codex exec review --output-schema` は **schema を無視して自然文を返す**。構造化が欲しいときは必ず③の `codex exec` + レビュー指示プロンプト方式を使う(公式 plugin の `/codex:review` は独自 schema・独自実行系で構造化しているので、それで足りるなら公式コマンドを K に案内する)
- `--full-auto` は help から隠された(非推奨化の兆候)ため使わない。承認プロンプトで詰まる場合のみ `-c approval_policy=on-failure` を付与

## §2 振り分け基準(いつ Claude / いつ Codex)

- **Claude Code(メイン)**: 探索・設計・実装・デバッグ・対話反復・ブラウザ/MCP/シート操作・ドキュメント
- **Codex(サブ)**: (1) PR 前のセカンドオピニオンレビュー(独立視点。公式 plugin) (2) 明確仕様の機械的バルク作業・調査の委譲(`codex:codex-rescue`) (3) セキュリティ/エッジケースの検算(③構造化レビュー) (4) Claude クォータ枯渇時のフォールバック
- 同一タスクの二重実行(bake-off)は高コストのため、設計判断が割れたときのみ

## §3 プロンプトの定型末尾指示(①③で必ず付与)

> 「確認や質問は不要です。具体的な提案・修正案・コード例まで自主的に出力してください。」

> 「ファイル検索に rg を使う場合は同梱の rg ではなく `/opt/homebrew/bin/rg`（brew版）を使ってください。」

（理由: Codex.app 同梱の rg は com.apple.quarantine 付きで macOS Gatekeeper に実行を弾かれる。brew 版は quarantine なし。2026-07-16 K指示）

※日本語出力は `~/.codex/AGENTS.md`(→ `~/.claude/AGENT.md` への symlink)で担保されるため個別指示不要。`codex:codex-rescue` へのプロンプトにも同様に不要(同じ AGENTS.md を読む)。

## §4 裏取りループ(③の後処理・必須)

**Codex の指摘は事実主張を裏取りしてから採用する。裏取りなしの指摘をそのまま K に転送したりコードに反映してはならない**(根拠: 2026-07-17 のレビュー実績で指摘の一部が意見レベルだった)。

1. `/tmp/codex-last.json` を Read し、`jq '.findings[]'` で分解する
2. 各 finding について: 実コードの file:line 前後を Read → `verify_hint` のコマンド/grep を実行 → verdict を付与
   - **confirmed**(事実確認済 → 採用) / **refuted**(誤り → 棄却、理由を記録) / **opinion**(意見レベル → K 判断行き)
3. 結果を表(id / file:line / severity / claim 要約 / verdict / 根拠)で K に報告。confirmed のみ修正に進む
4. `open_questions` と opinion は K へのゲート質問に束ねる(AGENT.md §2)
5. 公式 `/codex:review` 等の自然文レビューにも同じ規律を適用する(主張を手動抽出して裏取り)

## §5 書込委譲(`codex:codex-rescue`)の規律

- Claude 主導で使ってよい(K の逐次許可は不要。ただし AGENT.md §6「明確仕様のバルク作業」の範囲に留める — 曖昧な設計判断はここに投げない)
- 既定で write-capable。読み取り専用にしたい場合はプロンプトで明示する
- **大規模・広範囲・巻き戻し困難なバルク書込は worktree 隔離を既定とする**(Claude 側で git worktree を切り `--cd` で渡す。既存作業ツリーへの直接書込は、小規模で git diff 検収が容易な修正に限定)— 2026-08-04 棚卸し裁定で旧 AGENT.md §6「worktree 分離」を復活
- 完了後は **Claude 側が git diff レビュー+テスト実行で検収**してから統合する(subagent 自身は結果を右から左に転送するだけで検証しない)
- 大きい/長時間タスクは `--background` を付け、`/codex:status` `/codex:result`(K操作)または後続の rescue 呼び出しで確認する
- 継続指示は `--resume`、独立タスクは `--fresh` を明示する

## §6 出力ファイルの規約(本 Skill 分のみ)

- 結果は **ファイルが正**(stdout は進捗ログ扱い): ①= `/tmp/codex-last.md`、③= `/tmp/codex-last.json`。毎回上書き、並行実行時のみ suffix を付ける
- 実行後は必ず Read でファイル全文を読む(stdout の tail は長文で頭が切れる)

## §7 使用例

### ①設計相談
codex exec --sandbox read-only --cd /path/to/project -o /tmp/codex-last.md "このプロジェクトのアーキテクチャを分析して説明してください。確認や質問は不要です。改善提案まで自主的に出力してください。"

### ③構造化レビュー(PR 前)
codex exec --sandbox read-only --cd /path/to/project --output-schema ~/.claude/skills/codex/review-schema.json -o /tmp/codex-last.json "git diff main...HEAD で差分を確認しコードレビューしてください。観点: バグ・セキュリティ・エッジケース。確認や質問は不要です。ファイル検索に rg を使う場合は /opt/homebrew/bin/rg を使ってください。"

### 書込委譲(Agent tool 経由)
Agent(subagent_type: "codex:codex-rescue", prompt: "認証処理でトークン検証をスキップしているバグを調査し、最小のパッチで修正してください。")

### デザイン相談(UI/UX)
codex exec --sandbox read-only --cd /path/to/project -o /tmp/codex-last.md "あなたは世界トップクラスのUIデザイナーです。以下の観点からこのプロジェクトのUIを評価してください: (1) 視覚的階層構造とタイポグラフィ、(2) 余白・スペーシングのリズム、(3) カラーパレットのコントラストとアクセシビリティ、(4) インタラクションパターンの一貫性、(5) ユーザーの認知負荷の軽減。確認や質問は不要です。具体的な改善案をコード例付きで提示してください。"

codex exec --sandbox read-only --cd /path/to/project -o /tmp/codex-last.md "UXリサーチャー兼デザイナーとして、このフォームのユーザビリティを分析してください。Nielsen の10ヒューリスティクスに基づき、(1) エラー防止の仕組み、(2) ユーザーの制御と自由度、(3) 一貫性と標準、(4) 認識vs記憶の負荷、(5) 柔軟性と効率性を評価してください。確認や質問は不要です。改善したTailwind CSSコードまで自主的に提示してください。"

## §8 実行手順

1. 依頼内容を受け取り、§0 で公式 plugin(K操作 or Agent 委譲)と本 Skill のどちらの担当か判定する
2. 本 Skill 担当(①③)なら対象ディレクトリ/リポジトリルートを特定する
3. ①③はプロンプト末尾に §3 の定型指示を付与する
4. 実行し、出力ファイルを Read で全文読む(④は Agent tool の戻り値をそのまま読む)
5. ③・公式レビューは §4 の裏取りループを回す。④は diff レビュー+テストで検収する
6. 結果を K に報告(事実と意見を峻別、opinion は K ゲートへ)
