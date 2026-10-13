#!/usr/bin/env python3
"""指定日(JST)の Claude Code への発言をプロジェクトごとに出す。日報の素材集め用。
使い方: python3 -I history.py [YYYY-MM-DD]   (省略時は今日)"""
import collections, datetime, json, os, sys

JST = datetime.timezone(datetime.timedelta(hours=9))
day = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.datetime.now(JST).date()
by_project = collections.defaultdict(list)
with open(os.path.expanduser('~/.claude/history.jsonl')) as f:
    for line in f:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = datetime.datetime.fromtimestamp(d.get('timestamp', 0) / 1000, JST)
        text = d.get('display', '').strip()
        # スラッシュコマンド・exit・短い相槌は素材にならないので落とす
        if t.date() != day or text.startswith(('/', '!')) or text in ('exit', 'continue', 'OK', 'ok') or len(text) < 4:
            continue
        by_project[d.get('project', '?')].append(f"{t:%H:%M} {' '.join(text.split())[:300]}")
for project, lines in sorted(by_project.items(), key=lambda kv: kv[1][0]):
    print(f"## {project.replace(os.path.expanduser('~'), '~')} ({len(lines)})")
    print('\n'.join(lines))
