#!/usr/bin/env python3
"""離脱者一覧 CSV を生成する。

離脱 = Step "1-7" の登録 webhook が成立しなかった着信。折り返し架電の
検討材料として使えるよう、発信元番号とその種別・最終到達ステップを並べる。
発信元が媒体のフリーダイヤル（A経路）の行は本人番号ではないため架電できない。
"""
import csv

HEADER = ['着信日時', '夜間シフト日', '曜日', '発信元番号', '番号種別', '経路',
          '折り返し架電', '通話秒数', '最終到達ステップ', '1-6入力番号', '完了フラグ']

WD = ['月', '火', '水', '木', '金', '土', '日']

ROUTE_LABEL = {'A': 'A: 親番号媒体', 'B': 'B: 子番号直着信', 'anon': '非通知'}


def _tel(s):
    if not s:
        return ''
    if len(s) == 11:
        return f'{s[:3]}-{s[3:7]}-{s[7:]}'
    if len(s) == 10:
        return f'{s[:4]}-{s[4:7]}-{s[7:]}'
    return s


def reachable(c):
    """折り返し架電に使えるか。A経路の発信元は媒体のFDで本人番号ではない。"""
    if c['rt'] == 'B':
        return '可'
    if c['rt'] == 'A':
        return '不可（媒体FD）'
    return '不可（非通知）'


def rows(dropouts):
    for c in dropouts:
        yield [
            c['dt'].strftime('%Y-%m-%d %H:%M:%S'),
            c['shift'] or '',
            WD[c['dt'].weekday()],
            _tel(c['src']),
            c['kind'],
            ROUTE_LABEL.get(c['rt'], c['rt']),
            reachable(c),
            c['sec'],
            c['last_step'],
            _tel(c['entered']),
            c['flag'],
        ]


def write(dropouts, path, encoding='utf-8-sig'):
    """Excel でそのまま開けるよう既定は BOM 付き UTF-8。"""
    with open(path, 'w', encoding=encoding, newline='') as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows(dropouts))
    return len(dropouts)
