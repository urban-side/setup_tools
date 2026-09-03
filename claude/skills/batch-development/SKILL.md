---
name: batch-development
description: |
  バッチ / backfill / ETL / マイグレーション / 一括処理 の設計・実装時に参照する開発観点。
  トリガー: "バッチ", "backfill", "ETL", "マイグレーション", "一括更新", "一括取込", "一括書込"
  使用場面: (1) 外部 API と DB の整合を取るバッチ設計、(2) 大量データを扱う書込処理、(3) dry-run 付きバッチ、(4) 成功/失敗/skip を監査可能にする処理
---

# Batch / Backfill 開発観点

実務の backfill 開発での手戻り振り返りから抽出。

## 外部仕様は実物で検証してから設計

- 外部 API / OAS を扱う時は 1 リク実打ちした生 response を user と確認してから設計。OAS 定義と実 response は乖離する前提で動く。
- データ件数 / DB bind parameter 上限 / API ページング契約 (has_next ↔ end_cursor) は設計段階で BQ / 実 API で定量化。実装後発覚は設計やり直し。

## Observability は spec の一部として先に定義

- ログ / summary.json / dry-run / skip_reason / 「採用・要目視・skip」の分類 は spec 必須セクションとして schema を先に固定。実装後の追加は毎回スキーマ破壊を招く。
- 「採用+衝突検出」のような要監査ケースを "warn ログだけ" で流さない。監査可能な出力形式で残す。

## マッチング / 結合 / fail-fast は方式比較後に実装

- email → number → tie-break のような多段マッチングや fail-fast 閾値は 2 案以上の比較表で user 合意後に実装。
- fail-fast は「strict / normal / lenient」等の明示モードで切替可能に。dry-run 対応で緩めすぎて通常モード regression する前例あり。

## Codex レビューは spec 確定直後にも

- 実装完成後だけでなく spec / 設計確定直後にも codex にかける。設計段階で High/Medium (契約違反、重複検知漏れ、ページング異常) を排除しないと完成後レビューで 2-3 周の手戻り。

## CLI interface は設計で確定

- CLI flag / env / config の一覧 (`--mode`, `--dry-run`, `--csv-path`, `--bearer-token` 等) は設計段階で確定。後付け追加は使用側の追随コストを生む。

## テスト fixture

- 仕様 (マッチング方式等) が揺れている間は smoke test のみ。方式確定後に fixture を拡充。揺れ中の詳細テストは変更のたび書き直し。
