---
name: tanaoroshi
description: |
  定期棚卸し(AGENT.md §7.3)を実行する。対象: 全プロジェクトのメモリ / loops.md 台帳 / collect-queue / Skill /
  AGENT.md・CLAUDE.md / ~/temp 等の一時作業域 / plans・handover 残骸 / .claude 肥大 / 本仕組み(hook・Skill)自体。
  型: 収集→裏取り→裁定表→K承認→適用→検証。
  トリガー: "棚卸し", "/tanaoroshi", SessionStart リマインダー(tanaoroshi-reminder.sh)の期限超過通知
---

# 定期棚卸し手順

型: **収集(全読) → 裏取り(一次情報照合) → 裁定表 → K 承認(1 ゲート) → 適用 → 検証**。
実績: 2026-07-15 / 08-04 / 09-03 / 09-28(裁定表は `~/.claude/plans/tanaoroshi-<date>-saitei.md`)。

## 0. 原則

- 削除は K 承認後。裁定は 1 枚の裁定表(**A 削除リスト / B 台帳各行 / C メモリ / D その他**)に束ね、「推奨どおり」の一言で全適用できる形にする。推奨を付けられない項目は「K 裁定(推奨: …)」と明示し、未裁定のまま残った項目は loops.md に書く(§7.1)。
- 外部副作用(Linear 起票・コメント・PR・Slack 送信・remote ブランチ削除)は裁定表で個別に挙げる。承認が「文面準備」までなら `~/.claude/handover/tanaoroshi-<date>-drafts.md` に置いて止まる。
- 削除実行が権限機構に止められたら回避せず K に報告し、`! rm ...` の直接実行を提示する。
- 収集・裏取りは sonnet の Explore サブエージェントへ読み取り専用で委譲する(git fetch/pull・ビルド・書込み・push・チケット更新の禁止を明記)。Linear / Slack / Confluence の照合は MCP で自分が直接行う。

## 1. 収集(並列 3 本)

- **~/temp 等の一時作業域**: エントリ一覧 / git repo か / 未コミット・未 push / remote の有無 / 一次コード(どこにもバックアップがない実体)の識別 / サイズ / 最終更新。判定軸は「他所から再生成・再取得できるか」。平文の秘匿情報(creds・鍵)は必ず拾う。
- **~/.claude/projects/**: セッション数・最終活動 / MEMORY.md 索引と実ファイルの整合 / 孤児(作業 dir 消滅) / セッション 0 でメモリのみ。エンコード名の逆引きは `_`/`/` が `-` に潰れるため jsonl 内 cwd と test -d で確定する。
- **~/.claude 直下**: loops.md 全行 / collect-queue.md / skills と最終更新 / plans(.md は 30 日で自動削除される。メモリが参照する申し送り・設計原本は `~/.claude/handover/` へ退避) / handover/ の古い申し送り / du -d1 の上位。
- **仕組み自体**: AGENT.md・CLAUDE.md・本 Skill・hooks(tanaoroshi-reminder.sh / collect-session.sh)の陳腐化と実態との乖離(§7.3「本書自身」)。

## 2. 裏取り

- loops.md 各行とメモリの追跡事項を照合する。Linear は `list_issues(assignee=me, team=<自チーム>, includeArchived)` で一括取得し、旧 Jira キー→Linear ID の読み替え表を先に作る(移行前の履歴は Jira)。「K 回答待ち」「レビュー待ち」の行は当該 Slack スレッド・Confluence コメント(footer と inline の両方)を直接読むと決着していることが多い。
- GitHub の状態(ブランチ・PR・author)はローカルの remote-tracking でなく `gh api` / `gh pr` の live で判定する(fetch --prune 未実施の幽霊 ref が残る)。ローカル repo は最終 fetch 時点である旨を判定に添える。
- ドキュメント(HANDOVER・チケット本文・README)は鵜呑みにせず、実 PR・実コミット・実コードと突合する(§4)。アクセス不能(GCP 実体等)は「確認不能」と明記し、推測と事実を峻別する。

## 3. 裁定表(1 ゲート)

全文はファイルに書く。チャットには **A 削除リスト全件(ファイル名まで)・K 裁定項目(推奨付き)・集計・副次検出** を載せ、「推奨どおり」で通る形にする。副次検出(平文秘匿情報・露出継続・参照切れなど)は裁定不要でも必ず報告する。

## 4. 適用(承認分のみ)

- メモリ: 本文+frontmatter description+MEMORY.md 索引を同時更新(CLAUDE.md)。plans/ 参照は handover/ へ書換え、消滅済みは「(消滅)」注記。
- loops.md: 閉じた行は削除し、Open 冒頭の※行に変更サマリ(クローズ数と理由・削除実行物)を残す。全文の控えは `handover/loops-backup-<date>.md`。裁定で生まれた新規事項を追記。
- collect-queue.md: 昇格 / 台帳と重複 / 解消済み / 一過性 / Skill 候補(同種 2 回で採用・1 回は破棄)に分類し、集計を冒頭に残して空にする。
- 外部副作用は個別承認分のみ。承認が文面準備までなら drafts に置いて止まる。

## 5. 検証・完了

- 全 memory dir で MEMORY.md のリンク vs 実ファイルを突合し、`[[link]]` の切れも確認する。
- 削除後の ls / du 差分を報告。
- 元指示との逐項目突合せ表と差分(できなかったこと・K 回答待ち)を提示(§2)。
- 実施記録を更新: `date +%F > ~/.claude/.last-tanaoroshi`(SessionStart リマインダーがこれを参照)。
