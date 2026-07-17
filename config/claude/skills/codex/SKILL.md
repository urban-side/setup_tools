---
name: codex
description: |
  Codex CLI（OpenAI, gpt-5.6-sol）に相談・レビュー・検算・書込作業を依頼する。用途4分岐: ①汎用相談 ②クイックレビュー ③構造化レビュー(裏取りループ付き) ④書込ワーカー(writer profile)。
  トリガー: "codex", "codexと相談", "codexに聞いて", "codex review", "コードレビュー", "レビューして", "セカンドオピニオン", "構造化レビュー", "codexに任せて"
  使用場面: (1) PR前のセカンドオピニオンレビュー、(2) 文言・設計の相談、(3) バグ調査・検算、(4) 明確仕様のバルク作業の委譲
---

# Codex

Codex CLI(0.144.5 で検証)を Claude Code のサブとして使うスキル。振り分けの原則は AGENT.md §6 が正。

## §1 用途の判定表(まずここで分岐)

| 用途 | コマンド | 使いどころ |
|---|---|---|
| ①汎用相談 | `codex exec --sandbox read-only --cd <dir> -o /tmp/codex-last.md "<request>"` | 文言検討・設計相談・バグ調査・アーキ分析 |
| ②クイックレビュー | `cd <repo> && codex exec review --uncommitted -o /tmp/codex-last.md`(作業中)/ `--base <branch>`(PR前)/ `--commit <sha>` | 自然文レビューで足りるとき。**観点のカスタム指示は diff 指定フラグと排他**(0.144.5)— 観点が要るなら③へ |
| ③構造化レビュー | `codex exec --sandbox read-only --cd <repo> --output-schema ~/.claude/skills/codex/review-schema.json -o /tmp/codex-last.json "git diff <範囲> で差分を確認しコードレビューしてください。観点: <観点>。<定型末尾指示>"` | **PR 前の本命**。findings を JSON で受け、§4 の裏取りループを回す |
| ④書込ワーカー | `codex exec --profile writer --cd <worktree> -o /tmp/codex-last.md "<明確仕様の作業指示>"` | 明確仕様のバルク作業。**§5 の規律必須** |

注意(0.144.5 実測):
- `codex exec review --output-schema` は **schema を無視して自然文を返す**。構造化が欲しいときは必ず③の `codex exec` + レビュー指示プロンプト方式を使う
- review 系(②)に `--cd` は無い → リポジトリルートで `cd` してから実行
- `--full-auto` は help から隠された(非推奨化の兆候)ため使わない。承認プロンプトで詰まる場合のみ `-c approval_policy=on-failure` を付与

## §2 振り分け基準(いつ Claude / いつ Codex)

- **Claude Code(メイン)**: 探索・設計・実装・デバッグ・対話反復・ブラウザ/MCP/シート操作・ドキュメント
- **Codex(サブ)**: (1) PR 前のセカンドオピニオンレビュー(独立視点) (2) 明確仕様の機械的バルク作業(④・明示指示時のみ) (3) セキュリティ/エッジケースの検算 (4) Claude クォータ枯渇時のフォールバック
- 同一タスクの二重実行(bake-off)は高コストのため、設計判断が割れたときのみ

## §3 プロンプトの定型末尾指示(①③④で必ず付与)

> 「確認や質問は不要です。具体的な提案・修正案・コード例まで自主的に出力してください。」

> 「ファイル検索に rg を使う場合は同梱の rg ではなく `/opt/homebrew/bin/rg`（brew版）を使ってください。」

（理由: Codex.app 同梱の rg は com.apple.quarantine 付きで macOS Gatekeeper に実行を弾かれる。brew 版は quarantine なし。2026-07-16 K指示）

※日本語出力は `~/.codex/AGENTS.md`(→ `~/.claude/AGENT.md` への symlink)で担保されるため個別指示不要。

## §4 裏取りループ(③の後処理・必須)

**Codex の指摘は事実主張を裏取りしてから採用する。裏取りなしの指摘をそのまま K に転送したりコードに反映してはならない**(根拠: 2026-07-17 のレビュー実績で指摘の一部が意見レベルだった)。

1. `/tmp/codex-last.json` を Read し、`jq '.findings[]'` で分解する
2. 各 finding について: 実コードの file:line 前後を Read → `verify_hint` のコマンド/grep を実行 → verdict を付与
   - **confirmed**(事実確認済 → 採用) / **refuted**(誤り → 棄却、理由を記録) / **opinion**(意見レベル → K 判断行き)
3. 結果を表(id / file:line / severity / claim 要約 / verdict / 根拠)で K に報告。confirmed のみ修正に進む
4. `open_questions` と opinion は K へのゲート質問に束ねる(AGENT.md §2)
5. ②の自然文レビューにも同じ規律を適用する(主張を手動抽出して裏取り)

## §5 ④書込ワーカーの規律

- **K の明示指示があるときのみ**使う(勝手にバルク作業を委譲しない)
- 対象は git worktree 等で分離し、メイン作業ツリーを直接触らせない
- 完了後は **Claude 側が git diff レビュー+テスト実行で検収**してから統合する
- モデルは `~/.codex/writer.config.toml` で `gpt-5.6-sol` に明示ピン(K 指示)。上位モデル登場時はこのファイルを更新する
- profile 内容: model ピン / `sandbox_mode = "workspace-write"` / `approval_policy = "on-failure"`(network_access=false は base 継承)

## §6 出力ファイルの規約

- 結果は **ファイルが正**(stdout は進捗ログ扱い): ①②④= `/tmp/codex-last.md`、③= `/tmp/codex-last.json`。毎回上書き、並行実行時のみ suffix を付ける
- 実行後は必ず Read でファイル全文を読む(stdout の tail は長文で頭が切れる)

## §7 使用例

### ①設計相談
codex exec --sandbox read-only --cd /path/to/project -o /tmp/codex-last.md "このプロジェクトのアーキテクチャを分析して説明してください。確認や質問は不要です。改善提案まで自主的に出力してください。"

### ②クイックレビュー(作業中の未コミット差分)
cd /path/to/project && codex exec review --uncommitted -o /tmp/codex-last.md

### ③構造化レビュー(PR 前)
codex exec --sandbox read-only --cd /path/to/project --output-schema ~/.claude/skills/codex/review-schema.json -o /tmp/codex-last.json "git diff main...HEAD で差分を確認しコードレビューしてください。観点: バグ・セキュリティ・エッジケース。確認や質問は不要です。ファイル検索に rg を使う場合は /opt/homebrew/bin/rg を使ってください。"

### ④書込ワーカー(明示指示時のみ)
codex exec --profile writer --cd /path/to/worktree -o /tmp/codex-last.md "<仕様を逐字で>。他のファイルは変更しないでください。確認や質問は不要です。"

### デザイン相談(UI/UX)
codex exec --sandbox read-only --cd /path/to/project -o /tmp/codex-last.md "あなたは世界トップクラスのUIデザイナーです。以下の観点からこのプロジェクトのUIを評価してください: (1) 視覚的階層構造とタイポグラフィ、(2) 余白・スペーシングのリズム、(3) カラーパレットのコントラストとアクセシビリティ、(4) インタラクションパターンの一貫性、(5) ユーザーの認知負荷の軽減。確認や質問は不要です。具体的な改善案をコード例付きで提示してください。"

codex exec --sandbox read-only --cd /path/to/project -o /tmp/codex-last.md "UXリサーチャー兼デザイナーとして、このフォームのユーザビリティを分析してください。Nielsen の10ヒューリスティクスに基づき、(1) エラー防止の仕組み、(2) ユーザーの制御と自由度、(3) 一貫性と標準、(4) 認識vs記憶の負荷、(5) 柔軟性と効率性を評価してください。確認や質問は不要です。改善したTailwind CSSコードまで自主的に提示してください。"

## §8 実行手順

1. 依頼内容を受け取り、§1 の判定表で用途を決める(④は K の明示指示があるときのみ)
2. 対象ディレクトリ/リポジトリルートを特定する
3. ①③④はプロンプト末尾に §3 の定型指示を付与する
4. 実行し、出力ファイルを Read で全文読む
5. ③は §4 の裏取りループを回してから、②は主張を裏取りしてから報告する。④は diff レビュー+テストで検収する
6. 結果を K に報告(事実と意見を峻別、opinion は K ゲートへ)
