---
name: tanaoroshi
description: |
  定期棚卸し(AGENT.md §7.3)を実行する。対象: 全プロジェクトのメモリ / loops.md 台帳 / collect-queue / Skill /
  AGENT.md・CLAUDE.md / ~/temp・/tmp/claude-<uid> 等の一時作業域 / claude.ai の Artifact / plans・handover 残骸 / .claude 肥大 / 本仕組み(hook・Skill)自体。
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
  - **Claude の一時ファイル(`/tmp/claude-$(id -u)/` と `/tmp` 直下)**: 公式の自動削除は、`cleanupPeriodDays`(既定 30 日)の sweep が transcript と同時に消す scratchpad と、OS 再起動時の消去だけ。削除候補は (a) `<project>/<session-id>/`(配下の最終更新が 24h 以内のものと現セッションは稼働中とみなして除外) (b) `bundled-skills/` の現行版(`claude --version`)以外 (c) `/tmp` 直下の自分所有の残骸(セッションが scratchpad 外に書いた `*.md`・`*.log`・`*.diff`・`*.sh` 等)。scratchpad やタスク出力にしか無い成果物は削除前に退避要否を判定する。`cc-socks`・`cc-daemon-*`・`claude-mcp-browser-bridge-*`・`bash-edit-diff/` は稼働中プロセスが使うので対象外。macOS の `/tmp` は `/private/tmp` への symlink なので find は `/tmp/` で辿る。
- **~/.claude/projects/**: セッション数・最終活動 / MEMORY.md 索引と実ファイルの整合 / 孤児(作業 dir 消滅) / セッション 0 でメモリのみ / 全プロジェクトに効くべき feedback がプロジェクトメモリに閉じていないか(CLAUDE.md・AGENT.md への昇格候補)。エンコード名の逆引きは `_`/`/` が `-` に潰れるため jsonl 内 cwd と test -d で確定する。
- **~/.claude 直下**: loops.md 全行 / collect-queue.md / skills と最終更新 / plans(.md は 30 日で自動削除される。メモリが参照する申し送り・設計原本は `~/.claude/handover/` へ退避) / handover/ の古い申し送り / du -d1 の上位。
  - **外部由来の部品の鮮度**: plugin は `installed_plugins.json` の版と各 marketplace の upstream 最新(`gh api`)を比べる。auto-update が既定でオンなのは公式 marketplace だけで、third-party は手で更新しない限り古いまま。エージェントが呼ぶ CLI(codex 等)は `brew outdated --cask --greedy`、取り込んだ外部 Skill(stop-ai-slop-jp 等)は取り込んだ commit と upstream HEAD を比べる。
- **claude.ai の Artifact**: `Artifact list`(scope mine・limit 200)で全件を出し、各 ID を memory・loops.md・handover・`~/projects`・`~/temp` で検索する(`rg -F -f <ID一覧> -g '!*.jsonl' -g '!**/tool-results/**'`)。transcript と tool-results は作ったときの記録なので参照に数えない。loops.md は行の中身を読み、削除候補として挙げているだけの行も参照に数えない。社内の HTML 共有ツールは対象外(別途指示)。
- **仕組み自体**: AGENT.md・CLAUDE.md・本 Skill・hooks(tanaoroshi-reminder.sh / collect-session.sh)の陳腐化と実態との乖離(§7.3「本書自身」)。

## 2. 裏取り

- loops.md 各行とメモリの追跡事項を照合する。Linear は `list_issues(assignee=me, team=<自チーム>, includeArchived)` で一括取得し、旧 Jira キー→Linear ID の読み替え表を先に作る(移行前の履歴は Jira)。「K 回答待ち」「レビュー待ち」の行は当該 Slack スレッド・Confluence コメント(footer と inline の両方)を直接読むと決着していることが多い。
- GitHub の状態(ブランチ・PR・author)はローカルの remote-tracking でなく `gh api` / `gh pr` の live で判定する(fetch --prune 未実施の幽霊 ref が残る)。ローカル repo は最終 fetch 時点である旨を判定に添える。
- Skill・規約に書いた版・モデル名・設定値(「〜で検証」「現在 〜」)は実体と突合する。外部ツールを包む Skill はツール側の更新で黙って古くなる。照合先は `codex --version`・`~/.codex/config.toml`、plugin は `~/.claude/plugins/installed_plugins.json` の版と upstream HEAD(`gh api`)。
- 手元に参照がない Artifact は、Slack・Confluence・Linear を ID で検索してから判定する(DM で共有済みのものがある)。参照あり=残す / 参照なしで最終更新から 30 日超=A 削除リスト / 30 日以内=保留(作業中とみなす) / 私用で期日を過ぎたもの=削除候補。
- ドキュメント(HANDOVER・チケット本文・README)は鵜呑みにせず、実 PR・実コミット・実コードと突合する(§4)。アクセス不能(GCP 実体等)は「確認不能」と明記し、推測と事実を峻別する。

## 3. 裁定表(1 ゲート)

全文はファイルに書く。チャットには **A 削除リスト全件(ファイル名まで)・K 裁定項目(推奨付き)・集計・副次検出** を載せ、「推奨どおり」で通る形にする。副次検出(平文秘匿情報・露出継続・参照切れなど)は裁定不要でも必ず報告する。

## 4. 適用(承認分のみ)

- メモリ: 本文+frontmatter description+MEMORY.md 索引を同時更新(CLAUDE.md)。plans/ 参照は handover/ へ書換え、消滅済みは「(消滅)」注記。
- loops.md: 閉じた行は削除し、Open 冒頭の※行に変更サマリ(クローズ数と理由・削除実行物)を残す。全文の控えは `handover/loops-backup-<date>.md`。裁定で生まれた新規事項を追記。
- collect-queue.md: 昇格 / 台帳と重複 / 解消済み / 一過性 / Skill 候補(同種 2 回で採用・1 回は破棄)に分類し、集計を冒頭に残して空にする。
- Artifact: 削除は取り消せず、リンクも全員に対して切れる。`Artifact read`(out_dir=`~/.claude/handover/tanaoroshi-<date>-artifacts/`)で HTML を退避してから `Artifact delete` し、`Artifact list` を取り直して消えたことを確認する。
- 外部部品の更新: plugin は `claude plugin marketplace update <marketplace>` → `claude plugin update <plugin>@<marketplace>`、CLI は `brew upgrade --cask <name>`、取り込んだ Skill は upstream の差分を読んでから setup_tools の PR で入れ替える。更新後は §2 の版・設定値の突合をやり直す。
- 外部副作用は個別承認分のみ。承認が文面準備までなら drafts に置いて止まる。

## 5. 検証・完了

- 全 memory dir で MEMORY.md のリンク vs 実ファイルを突合し、`[[link]]` の切れも確認する。
- 削除後の ls / du 差分を報告。
- 元指示との逐項目突合せ表と差分(できなかったこと・K 回答待ち)を提示(§2)。
- 実施記録を更新: `date +%F > ~/.claude/.last-tanaoroshi`(SessionStart リマインダーがこれを参照)。
