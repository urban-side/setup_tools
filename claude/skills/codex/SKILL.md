---
name: codex
description: |
  Codex CLI（OpenAI。モデルはプロバイダー既定）に相談・検算・書込作業を委譲する。相談・書込委譲・構造化レビュー(裏取りループ付き)を、すべて `codex exec` で行う。
  トリガー: "codex", "codexと相談", "codexに聞いて", "codex review", "コードレビュー", "レビューして", "セカンドオピニオン", "構造化レビュー", "codexに任せて", "codexに調査させて"
  使用場面: (1) 文言・設計の相談、(2) PR前の構造化セカンドオピニオン(裏取り前提)、(3) 明確仕様のバルク作業・調査の委譲
---

# Codex

Codex CLI(0.162.1 で検証・2026-10-13)を Claude Code のサブとして使うスキル。Claude×Codex の振り分け基準は本 Skill §2 が正(AGENT.md §6 は一般原則のみ)。

公式 plugin `codex@openai-codex`(openai/codex-plugin-cc)は使わない。2026-07-08 の v1.0.6 以降マージが止まり、open の issue と PR がそれぞれ 100 件を超えている(2026-10-13 確認)。全用途を本 Skill の `codex exec` で賄う。

## §1 用途と呼び方

| 用途 | コマンド | 使いどころ |
|---|---|---|
| ①汎用相談 | `codex exec --sandbox read-only --cd <dir> -o <scratchpad>/codex-last.md "<request>" < /dev/null` | 文言検討・設計相談・バグ調査・アーキ分析(レビュー枠に収まらない自由形式) |
| ②書込委譲 | `codex exec --sandbox workspace-write --cd <dir> -o <scratchpad>/codex-write.md "<仕様>" < /dev/null` | 明確仕様のバルク作業・調査と修正。規律は §5 |
| ③構造化レビュー | `codex exec --sandbox read-only --cd <repo> --output-schema ~/.claude/skills/codex/review-schema.json -o <scratchpad>/codex-last.json "git diff <範囲> で差分を確認しコードレビューしてください。観点: <観点>。<定型末尾指示>" < /dev/null` | **PR 前の本命**。findings を JSON で受け、§4 の裏取りループを回す。設計を疑わせたいときは観点に書く |

`<scratchpad>` はセッションの scratchpad ディレクトリ(システムプロンプトに書かれている)。`/tmp` 直下に書くと誰も消さずに残る。

モデルはピンせずプロバイダー既定に任せる(`~/.codex/config.toml` に `model` 行を置かない。K裁定 2026-10-12。旧ピン `gpt-6.1-sol` は ChatGPT アカウントで 400 になり全呼び出しが止まった)。`-m` も原則付けない。推論強度の既定は `~/.codex/config.toml` の `model_reasoning_effort` で、値は実物を見る。既定より上げたい設計相談だけ `-c model_reasoning_effort=high` を付ける。

注意:
- **非対話実行では `< /dev/null` を必ず付ける。** 付けないと `Reading additional input from stdin...` で追加入力を待ち続けて進まない(0.154.0 で実測・2026-09-17)
- `codex exec review --output-schema` は **schema を無視して自然文を返す**(0.144.5 実測)。構造化が欲しいときは③の `codex exec` + レビュー指示プロンプト方式を使う
- `--full-auto` は help から隠された(非推奨化の兆候)ため使わない。承認プロンプトで詰まる場合のみ `-c approval_policy=on-failure` を付与

## §2 振り分け基準(いつ Claude / いつ Codex)

- **Claude Code(メイン)**: 探索・設計・実装・デバッグ・対話反復・ブラウザ/MCP/シート操作・ドキュメント
- **Codex(サブ)**: (1) PR 前のセカンドオピニオンレビュー(独立視点。③) (2) 明確仕様の機械的バルク作業・調査の委譲(②) (3) セキュリティ/エッジケースの検算(③) (4) Claude クォータ枯渇時のフォールバック
- 同一タスクの二重実行(bake-off)は高コストのため、設計判断が割れたときのみ

## §3 プロンプトの定型末尾指示(①②③で必ず付与)

> 「確認や質問は不要です。具体的な提案・修正案・コード例まで自主的に出力してください。」

> 「ファイル検索に rg を使う場合は同梱の rg ではなく `/opt/homebrew/bin/rg`（brew版）を使ってください。」

（理由: Codex.app 同梱の rg は com.apple.quarantine 付きで macOS Gatekeeper に実行を弾かれる。brew 版は quarantine なし。2026-07-16 K指示）

※日本語出力は `~/.codex/AGENTS.md`(→ `~/.claude/AGENT.md` への symlink)で担保されるため個別指示不要。

## §4 裏取りループ(③の後処理・必須)

**Codex の指摘は事実主張を裏取りしてから採用する。裏取りなしの指摘をそのまま K に転送したりコードに反映してはならない**(根拠: 2026-07-17 のレビュー実績で指摘の一部が意見レベルだった)。指摘を出したあとは止まり、直す前に K に確認する。自動適用はしない。

1. `<scratchpad>/codex-last.json` を Read し、`jq '.findings[]'` で分解する
2. 各 finding について: 実コードの file:line 前後を Read → `verify_hint` のコマンド/grep を実行 → verdict を付与
   - **confirmed**(事実確認済 → 採用) / **refuted**(誤り → 棄却、理由を記録) / **opinion**(意見レベル → K 判断行き)
3. 結果を表(id / file:line / severity / claim 要約 / verdict / 根拠)で K に報告。confirmed のみ修正に進む
4. `open_questions` と opinion は K へのゲート質問に束ねる(AGENT.md §2)
5. ①で返ってきた自然文の指摘にも同じ規律を適用する(主張を手動抽出して裏取り)

## §5 書込委譲(②)の規律

- Claude 主導で使ってよい(K の逐次許可は不要。ただし AGENT.md §6「明確仕様のバルク作業」の範囲に留める — 曖昧な設計判断はここに投げない)
- 書けるのは `--cd` で渡したディレクトリ配下だけ。読み取りだけさせたいときは①を使う
- **大規模・広範囲・巻き戻し困難なバルク書込は worktree 隔離を既定とする**(Claude 側で git worktree を切り `--cd` で渡す。既存作業ツリーへの直接書込は、小規模で git diff 検収が容易な修正に限定)— 2026-08-04 棚卸し裁定で旧 AGENT.md §6「worktree 分離」を復活
- 完了後は **Claude 側が git diff レビュー+テスト実行で検収**してから統合する。Codex 自身の「完了しました」は検収にならない
- 長時間タスクは Bash の `run_in_background` で流し、完了通知を待ってから `-o` のファイルを読む
- 継続指示は `codex exec resume --last "<追加指示>"`(並行実行しているときはセッション ID を指定)。独立タスクは新しい `codex exec` で始める

## §6 出力ファイルの規約

- 結果は **ファイルが正**(stdout は進捗ログ扱い): ①= `<scratchpad>/codex-last.md`、②= `<scratchpad>/codex-write.md`、③= `<scratchpad>/codex-last.json`。毎回上書き、並行実行時のみ suffix を付ける
- 実行後は必ず Read でファイル全文を読む(stdout の tail は長文で頭が切れる)

## §7 使用例

### ①設計相談
codex exec --sandbox read-only --cd /path/to/project -o <scratchpad>/codex-last.md "このプロジェクトのアーキテクチャを分析して説明してください。確認や質問は不要です。改善提案まで自主的に出力してください。" < /dev/null

### ②書込委譲
codex exec --sandbox workspace-write --cd /path/to/worktree -o <scratchpad>/codex-write.md "認証処理でトークン検証をスキップしているバグを調査し、最小のパッチで修正してください。確認や質問は不要です。ファイル検索に rg を使う場合は /opt/homebrew/bin/rg を使ってください。" < /dev/null

### ③構造化レビュー(PR 前)
codex exec --sandbox read-only --cd /path/to/project --output-schema ~/.claude/skills/codex/review-schema.json -o <scratchpad>/codex-last.json "git diff main...HEAD で差分を確認しコードレビューしてください。観点: バグ・セキュリティ・エッジケース。確認や質問は不要です。ファイル検索に rg を使う場合は /opt/homebrew/bin/rg を使ってください。" < /dev/null

### デザイン相談(UI/UX)
codex exec --sandbox read-only --cd /path/to/project -o <scratchpad>/codex-last.md "あなたは世界トップクラスのUIデザイナーです。以下の観点からこのプロジェクトのUIを評価してください: (1) 視覚的階層構造とタイポグラフィ、(2) 余白・スペーシングのリズム、(3) カラーパレットのコントラストとアクセシビリティ、(4) インタラクションパターンの一貫性、(5) ユーザーの認知負荷の軽減。確認や質問は不要です。具体的な改善案をコード例付きで提示してください。" < /dev/null

codex exec --sandbox read-only --cd /path/to/project -o <scratchpad>/codex-last.md "UXリサーチャー兼デザイナーとして、このフォームのユーザビリティを分析してください。Nielsen の10ヒューリスティクスに基づき、(1) エラー防止の仕組み、(2) ユーザーの制御と自由度、(3) 一貫性と標準、(4) 認識vs記憶の負荷、(5) 柔軟性と効率性を評価してください。確認や質問は不要です。改善したTailwind CSSコードまで自主的に提示してください。" < /dev/null

## §8 実行手順

1. 依頼内容を受け取り、§1 で①②③のどれかを決める
2. 対象ディレクトリ/リポジトリルートを特定する(②で広範囲に書くなら worktree を切る)
3. プロンプト末尾に §3 の定型指示を付与する
4. 実行し、出力ファイルを Read で全文読む
5. ③と①の指摘は §4 の裏取りループを回す。②は git diff レビュー+テストで検収する
6. 結果を K に報告(事実と意見を峻別、opinion は K ゲートへ)
