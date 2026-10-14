---
name: nippo
description: |
  K の日報を Notion(しごと/<会社名>/日報)に書く。その日の Claude Code の発言・GitHub・Linear・Slack・Confluence から「今日やったこと」を、社内のニュース系チャンネルから「学んだこと・アンテナ」を組み立て、K の書き方に揃えて追記する。
  トリガー: "日報", "/nippo", "日報書いて", "日報つけて", "今日の日報", "昨日の日報"
---

# nippo

日報 DB にその日のページを作るか、既にあれば足りない項目だけを追記する。書き方の正は `references/style.md`。先に読む。

## 固定値

| 対象 | 値 |
|---|---|
| 日報 DB(data source) | `collection://<NOTION_DATA_SOURCE_ID>` |
| ページ名 / 日付 | `日報_YYYYMMDD` / プロパティ `Date`(日付のみ) |
| K の Slack ユーザー | `<SLACK_USER_ID>` |
| Times | `#z-times-<名前>`(`<TIMES_CHANNEL_ID>`) |
| アンテナの取り元 | 技術ニュースの bot チャンネル(`<NEWS_CHANNEL_ID>`)・技術雑談(`<CHAT_CHANNEL_ID>`)・技術告知(`<ANNOUNCE_CHANNEL_ID>`)・自社の報道(`<PRESS_CHANNEL_ID>`) |
| Confluence | cloudId `<SITE>.atlassian.net` |
| GitHub | org `<GITHUB_ORG>` だけを見る(個人 repo は日報に書かない) |

Notion の `notion-query-data-sources` は SQL モードを使わない。Business プラン未満だとワークスペース共通の回数上限があり、すぐ尽きる(view モードは数えられない)。ページ探しは `notion-search` で行う。

## 手順

### 1. 対象日を決める

引数の日付(`2026-10-13` / `昨日` など)。無ければ今日(JST)。以下 `DATE` と書く。

### 2. 材料を集める(並列でよい)

| 材料 | 取り方 | 使い道 |
|---|---|---|
| Claude Code の発言 | `python3 -I ~/.claude/skills/nippo/history.py DATE` | 何に時間を使ったかの骨組み。プロジェクト単位でまとまっている |
| PR | `~/.claude/skills/nippo/prs.sh DATE` | 作った PR・マージされた PR・その日にレビューした PR |
| Linear | `mcp__linear__list_issues`(assignee `me`、updatedAt に DATE の 0:00 JST を UTC で。「この時刻以降」の意味なので、過去日なら翌日以降の更新を落とす) | チケット単位の見出し |
| Slack の発言 | `slack_search_public_and_private`、filters `from:<@<SLACK_USER_ID>> on:DATE`。Times と勤怠連絡のチャンネルは除く | リリース・障害・告知・相談。リンクを子項目に貼る |
| Confluence | CQL `contributor = currentUser() AND lastmodified >= "DATE" AND lastmodified < "DATE+1" AND type = page` | 定例・勉強会の議事録、設計書。contributor は「過去に一度でも編集した人」なので、その日に誰かが更新しただけのページも混ざる。K の発言・Slack と突き合わせて、K が触ったと言えるものだけ使う |
| アンテナ | 上の 4 チャンネルを `slack_read_channel` で読む。oldest と latest には DATE の 0:00 JST と翌日 0:00 JST の Unix 時刻を渡す。技術ニュースの bot チャンネルは 1 日 60 件前後あり、結果がファイルに逃がされるので、題と URL と時刻を抜き出してから読む | アンテナの素材 |
| 既存ページ | `notion-search`(query `日報_YYYYMMDD`、data_source_url は上の DB)で題名が `日報_YYYYMMDD` で始まるものを探し、あれば `notion-fetch` | K が手で書いた行を残すため |

### 3. 組み立てる

`references/style.md` の型に沿って 3 節を作る。

- **今日やったこと**: 1 つの仕事 = 最上位の項目 1 つ。チケットがあればチケット URL を最上位に置き、PR を子に並べる。会議は会議名を最上位に、議事録のリンクを子に置く。発言だけで成果物の無い作業(調査・相談)は、短い名詞句 1 行で書く。
- **学んだこと・アンテナ**: 社内チャンネルの記事から 2〜4 個と、作業で踏んだ仕様の技術メモを 0〜1 個。選び方は style.md。条件に合う記事が無い日は 0 個でよく、数合わせで拾わない。K の Times は使わない。
- **次回のタスク**: 原則空。K がその日に「明日やる」「次は〜」と言った作業がはっきりあるときだけ書く。

書かないもの: 認証情報やトークン、顧客の電話番号や氏名などの個人情報、1on1・評価・面接の中身、離席や戻りの連絡、雑談。

### 4. 推敲する

自分で書いた地の文(子項目の一言メモ・アンテナの一言)に stop-ai-slop-jp の規則を当てる。日報は業務メモなので、ブログ向けの規則(伝聞の「らしい」を混ぜる・毒や自虐を足す・中間温度の語を足す・文末のムラ付け)は外す。記事の題は元の題のまま使い、言い換えない。

### 5. 書き込む

- **ページが無い**: `notion-create-pages`。parent は `{"data_source_id": "<NOTION_DATA_SOURCE_ID>"}`、properties は `Name`=`日報_YYYYMMDD`・`date:Date:start`=DATE・`date:Date:is_datetime`=0。テンプレートは使わず(非同期で後から本文が入るため)、3 つの見出しを本文に直接書く。
- **ページがある**: K の行は消さない・書き換えない・並べ替えない。既にある URL と同じ URL を持つ項目と、K が別の言葉で書いた同じ仕事は足さない。既存ページの Slack リンクは `slackMessage://<WORKSPACE>.slack.com/<チャンネルID>/<ts>/<thread_ts>` の形で返るので、チャンネル ID と ts で突き合わせる(書き込んだ https の Slack URL も、保存後はこの形に変わる)。`notion-update-page` の `update_content` で、次の見出しの直前に差し込む(例: old_str `# 学んだこと・アンテナ` → new_str `<追記する項目>\n# 学んだこと・アンテナ`)。見出しの直前に空の箇条書き `-` や `<empty-block/>` があれば、それも old_str に含めて置き換える。最後の節は `insert_content`(末尾)で足す。
- 入れ子はタブ。リンクは `[URL](URL)` の形で、URL をそのままリンク文字にする。Linear は `https://linear.app/<WORKSPACE>/issue/TEAM-1234` の短い形にする。Slack の permalink は検索結果だと `<ORG>.enterprise.slack.com` になるので、K が貼る形の `https://<WORKSPACE>.slack.com/archives/<チャンネルID>/p<ts>`(スレッド返信は `?thread_ts=…&cid=…` を残す)に直す。

### 6. 報告する

ページの URL と、追記した行をそのまま見せる。材料にあったが入れなかったもの(判断に迷ったもの)があれば 1 行ずつ添える。
