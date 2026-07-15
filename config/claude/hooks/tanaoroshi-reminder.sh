#!/bin/sh
# 月次棚卸しリマインダー (AGENT.md §7.3 / tanaoroshi Skill とセット)
# ~/.claude/.last-tanaoroshi (YYYY-MM-DD 1行) が 30 日超過なら、
# SessionStart でセッション冒頭のコンテキストに注意喚起を注入する。
# 期限内は何も出力しない(無音)。実施記録の更新は tanaoroshi Skill の完了手順が行う。
MARKER="$HOME/.claude/.last-tanaoroshi"
THRESHOLD_DAYS=30

if [ ! -f "$MARKER" ]; then
  echo "【棚卸しリマインダー】定期棚卸し(AGENT.md §7.3)の実施記録(~/.claude/.last-tanaoroshi)がありません。K に /tanaoroshi の実施を提案してください。"
  exit 0
fi

last_date=$(head -1 "$MARKER" | tr -d '[:space:]')
last_epoch=$(date -j -f "%Y-%m-%d" "$last_date" "+%s" 2>/dev/null) || exit 0
now_epoch=$(date "+%s")
days=$(( (now_epoch - last_epoch) / 86400 ))

if [ "$days" -ge "$THRESHOLD_DAYS" ]; then
  echo "【棚卸しリマインダー】前回の定期棚卸し(${last_date})から ${days} 日経過し、月次目安(AGENT.md §7.3)を超過しています。K に /tanaoroshi の実施を提案してください。"
fi
exit 0
