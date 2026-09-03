#!/bin/bash
# SessionEnd hook: セッションから Skill 候補(差戻し)とオープンループ(宙吊り事項)を
# haiku で抽出し ~/.claude/collect-queue.md に追記する。
# キューの回収(採用判断)は定期棚卸しで K が行う。AGENT.md §7 参照。
set -u

# 収集用ヘッドレスセッション自身の SessionEnd で再帰しないためのガード
[ -n "${CLAUDE_COLLECTOR:-}" ] && exit 0

LOG=~/.claude/hooks/collect.log
input=$(cat)
transcript=$(echo "$input" | jq -r '.transcript_path // empty' 2>>"$LOG")
cwd=$(echo "$input" | jq -r '.cwd // empty' 2>>"$LOG")
[ -f "$transcript" ] || exit 0

# K の実発言のみ抽出(tool_result・コマンド残骸・通知を除外)
turns=$(jq -r 'select(.type=="user") | .message.content
  | if type=="string" then . else ([.[]? | select(.type=="text") | .text] | join("\n")) end' \
  "$transcript" 2>>"$LOG" \
  | grep -v -e '<local-command' -e '<command-name>' -e '<bash-input>' -e '^Caveat:' \
            -e '<system-reminder>' -e '<task-notification>' -e '^\[Request interrupted')

# 発言が少ないセッション(即 exit 等)は収集しない
n=$(printf '%s' "$turns" | grep -c '[^[:space:]]')
[ "$n" -lt 3 ] && exit 0

prompt='以下の <turns> はユーザーKとエージェントのセッションにおけるKの発言集です。次の2種だけを抽出してください。
- 「[skill候補] 〜」: Kがエージェントのやり方・成果物を差戻し/訂正した箇所(何をどう直させたか、1件1行)
- 「[loop] 〜」: 宙に浮いたままの事項(未回答の確認・提案、「あとで」「別途」「要確認」「暫定」とされた値や作業)
出力規則(厳守): 各行を必ず [skill候補] または [loop] で始める。それ以外の行(前置き・解説・見出し・要約)は一切出力しない。該当なしなら NONE とだけ出力。確実なものだけ。'

out=$(
  { printf '<turns>\n'; printf '%s' "$turns" | head -c 50000; printf '\n</turns>\n'; } \
  | CLAUDE_COLLECTOR=1 claude -p "$prompt" --model claude-haiku-4-5-20251001 2>>"$LOG")
rc=$?
[ $rc -ne 0 ] && { echo "$(date +%FT%T) claude -p failed rc=$rc cwd=$cwd" >>"$LOG"; exit 0; }

# 形式検証: [skill候補]/[loop] で始まる行だけ通す(モデルの指示逸脱をここで遮断)
filtered=$(printf '%s\n' "$out" | grep -E '^[[:space:]]*[-*]?[[:space:]]*\[(skill候補|loop)\]' )
[ -z "$filtered" ] && exit 0

{
  echo "## $(date +%F) ${cwd:-unknown}"
  echo "$filtered"
  echo
} >> ~/.claude/collect-queue.md
exit 0
