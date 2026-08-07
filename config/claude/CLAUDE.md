# 規約

全エージェント共通の行動規約の正は AGENT.md(下記インポート)。本ファイルは Claude Code 固有の補足のみを持つ。

@~/.claude/AGENT.md

# Claude Code 固有

- モデル割当: 最上位モデル(Fable 等)は設計・レビュー・意思決定。サブエージェントへの委譲時は作業難易度に応じたモデルを明示指定する — 機械的な読取・収集・定型変換=haiku / 実装・調査の標準=sonnet(既定) / 高難度実装・検証がクリティカルな作業=opus。迷ったら一段上(下位モデルの失敗はやり直しで高くつく)。
- PR 作成手順の詳細は create-pr Skill に従う。
- Codex 連携(振り分け・裏取りループ・書込委譲)は codex Skill に従う。
- メモリ衛生: 本文を更新したら frontmatter description と MEMORY.md 索引行も同時に更新する(乖離が最頻の腐敗モード)。前提が覆ったら旧記述に訂正を追記し相互リンク。チケット完了・PR マージを見届けたら追跡メモに完了を明記する。
- 定期棚卸しの実施機構: SessionStart hook(tanaoroshi-reminder.sh)が ~/.claude/.last-tanaoroshi の 30 日超過で注意喚起(2026-07-15 導入)。Skill 候補・オープンループは SessionEnd hook(collect-session.sh)が collect-queue.md へ自動収集し、採用判断は棚卸しで K が行う。
