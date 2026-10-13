#!/bin/bash
# 指定日(JST)に K が作った / マージに関わった / レビューした PR を出す。日報の素材集め用。
# 使い方: prs.sh [YYYY-MM-DD]   (省略時は今日)
set -u
d=${1:-$(TZ=Asia/Tokyo date +%F)}
org=example-org  # 実際の GitHub org に置き換える
fmt='.[] | "\(.repository.name)#\(.number) [\(.state)] \(.title) \(.url)"'
echo "## 作った"
gh search prs --owner=$org --author=@me --created="$d" --json repository,number,title,state,url --limit 50 --jq "$fmt"
echo "## マージされた(関わったもの)"
gh search prs --owner=$org --involves=@me --merged-at="$d" --json repository,number,title,state,url --limit 50 --jq "$fmt"
echo "## レビューした(他人の PR・その日に出したレビューだけ)"
me=$(gh api user --jq .login)
gh search prs --owner=$org --reviewed-by=@me --updated=">=$d" --json repository,number,title,author,url --limit 50 \
  --jq ".[] | select(.author.login != \"$me\") | \"\(.repository.name) \(.number) \(.title) \(.url)\"" |
while read -r repo num rest; do
  # --updated は bot の更新でも当たるので、レビューの提出日(JST)で絞る
  n=$(gh api "repos/$org/$repo/pulls/$num/reviews" --jq "[.[] | select(.user.login==\"$me\") | .submitted_at] | .[]" |
      while read -r t; do TZ=Asia/Tokyo date -j -f %Y-%m-%dT%H:%M:%SZ -v+9H "$t" +%F 2>/dev/null; done | grep -c "^$d$")
  if [ "$n" -gt 0 ]; then echo "$repo#$num $rest"; fi
done
