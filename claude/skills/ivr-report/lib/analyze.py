#!/usr/bin/env python3
"""IVR コールログ CSV の集計。

受電数に対する電話番号登録（Step "1-7" の登録 webhook が 200 / result=OK）の
割合を、経路・日別・夜間シフト・時間帯の各軸で集計する。

経路分類:
  A = 発信元が 0120/0800（クライアント側回線からの転送。発信元 ≠ 本人番号）
  B = それ以外の発信元通知あり（発信元 ≒ 本人番号）
  非通知 = 主集計から分離して別掲（テスト・ボット疑いを含むため）

テナントごとに CSV の列構成が異なるため、固定インデックスではなくヘッダ名で
列を解決する。解決に失敗した場合は明示的にエラー終了する。
"""
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from holidays import is_dayoff

WD = ['月', '火', '水', '木', '金', '土', '日']

# ヘッダ完全一致で解決する列（テナント間で共通の列名）
EXACT_COLS = {
    'ID': 'ID',
    'CALLID': 'Call ID',
    'RECV': '着信日時',
    'SEC': '通話秒数',
    'SRC': '発信元番号',
    'FLAG': '完了フラグ',
}

# 経路・シナリオを問わずメタ情報として扱う列（残りをシナリオのステップ列とみなす）
META_COLS = {
    'ID', 'Call ID', '着信日時', '切断日時', '通話秒数', '着信先番号', '発信元番号',
    'シナリオID', 'シナリオ名', 'パートナーID', 'パートナー名',
    'アカウントID', 'アカウント名', '完了フラグ',
}

ENCODINGS = ('utf-8-sig', 'cp932', 'utf-8')


class LogFormatError(Exception):
    """CSV が IVR コールログの形式として解釈できない。"""


def digits(s):
    return re.sub(r'\D', '', s or '')


def number_kind(d):
    """発信元番号の種別。架電先として使えるかの目安。"""
    if not d:
        return '非通知'
    if d.startswith(('0120', '0800', '0037')):
        return 'フリーダイヤル'
    if d.startswith(('090', '080', '070')):
        return '携帯'
    if d.startswith('050'):
        return 'IP電話'
    return '固定電話'


def open_csv(path):
    """IVR 事業者の書き出しは UTF-8 と CP932 の両方がありうるため順に試す。"""
    last = None
    for enc in ENCODINGS:
        try:
            with open(path, encoding=enc) as f:
                f.read()
            return open(path, encoding=enc), enc
        except UnicodeDecodeError as e:
            last = e
    raise LogFormatError(f'[{path}] 文字コードを判別できません（{ENCODINGS} を試行）: {last}')


def resolve_columns(header, path):
    """CSV ヘッダから必要な列インデックスを名前解決する。解決失敗時は例外。"""
    col = {}
    for key, name in EXACT_COLS.items():
        try:
            col[key] = header.index(name)
        except ValueError:
            raise LogFormatError(
                f'[{path}] ヘッダ列が見つかりません（完全一致必須）: {name!r}\n'
                f'  実際のヘッダ: {header}')

    def find_unique(require_all, exclude, label):
        cands = [i for i, h in enumerate(header)
                 if all(s in h for s in require_all) and exclude not in h]
        if len(cands) != 1:
            raise LogFormatError(
                f'[{path}] {label} 列の解決に失敗（候補{len(cands)}件）: '
                f'{[header[i] for i in cands]}\n  実際のヘッダ: {header}')
        return cands[0]

    col['S16'] = find_unique(['1-6', '電話番号入力'], '入力値', '"1-6" 電話番号入力')
    col['S17'] = find_unique(['1-7', '電話番号通知'], '入力値', '"1-7" 電話番号通知')
    # ステップ列 = メタ列でも「〜入力値」でもない列。CSV の並び順がシナリオ順。
    steps = [(i, h) for i, h in enumerate(header)
             if h not in META_COLS and not h.endswith('入力値') and h.strip()]
    col['STEPS'] = steps
    return col


def enrich(row, col):
    dt = datetime.strptime(row[col['RECV']], '%Y-%m-%d %H:%M:%S')
    src = digits(row[col['SRC']])
    reached = [name for i, name in col['STEPS'] if (row[i] or '').strip()]
    s17 = row[col['S17']] or ''
    return dict(
        dt=dt, date=dt.strftime('%Y-%m-%d'), hour=dt.hour,
        sec=int(row[col['SEC']] or 0),
        src=src, kind=number_kind(src),
        rt='anon' if not src else ('A' if src.startswith(('0120', '0800')) else 'B'),
        entered=digits(row[col['S16']]),
        s16=bool(row[col['S16']]),
        ok=s17.startswith('200') and 'result=OK' in s17,
        flag=row[col['FLAG']],
        reached=reached,
        last_step=reached[-1] if reached else '(ステップ記録なし)',
        shift=(dt.strftime('%Y-%m-%d') if dt.hour >= 20
               else (dt - timedelta(days=1)).strftime('%Y-%m-%d') if dt.hour < 8
               else None),
    )


def load_calls(paths):
    """CSV 群を読み込む。ファイルごとにヘッダから列を解決し、ID で重複排除する。

    returns: (calls, meta)
    """
    seen, calls = set(), []
    dup = 0
    step_names, encodings, scenarios = [], {}, Counter()
    for p in paths:
        f, enc = open_csv(p)
        encodings[p] = enc
        with f:
            r = csv.reader(f)
            try:
                header = next(r)
            except StopIteration:
                raise LogFormatError(f'[{p}] 空のファイルです')
            col = resolve_columns(header, p)
            names = [n for _, n in col['STEPS']]
            for n in names:
                if n not in step_names:
                    step_names.append(n)
            sc = header.index('シナリオ名') if 'シナリオ名' in header else None
            for row in r:
                if not row:
                    continue
                rid = row[col['ID']]
                if rid in seen:  # 月跨ぎファイル等の重複行を排除
                    dup += 1
                    continue
                seen.add(rid)
                if sc is not None and len(row) > sc:
                    scenarios[row[sc]] += 1
                calls.append(enrich(row, col))
    if not calls:
        raise LogFormatError('データ行が 1 件もありません')
    calls.sort(key=lambda c: c['dt'])
    meta = dict(files=list(paths), encodings=encodings, dup_removed=dup,
                step_names=step_names, scenarios=scenarios.most_common(),
                first=calls[0]['date'], last=calls[-1]['date'], rows=len(calls))
    return calls, meta


def day_type_match(ds, day_type):
    if day_type == 'weekday':
        return not is_dayoff(ds)
    if day_type == 'holiday':
        return is_dayoff(ds)
    return True


def rate(n, d):
    return round(100.0 * n / d, 1) if d else None


def block(calls):
    total = len(calls)
    nz = [c for c in calls if c['sec'] > 0]
    okc = [c for c in calls if c['ok']]
    a = [c for c in calls if c['rt'] == 'A']
    b = [c for c in calls if c['rt'] == 'B']
    b_src = set(c['src'] for c in b)
    b_src_ok = set(c['src'] for c in b if c['ok'])
    return dict(
        calls=total, calls_nz=len(nz), ok=len(okc),
        s16=sum(1 for c in calls if c['s16']),
        a_calls=len(a), b_calls=len(b), anon=total - len(a) - len(b),
        a_ok=sum(1 for c in a if c['ok']), b_ok=sum(1 for c in b if c['ok']),
        a_zero=sum(1 for c in a if c['sec'] == 0), b_zero=sum(1 for c in b if c['sec'] == 0),
        b_persons=len(b_src), b_persons_ok=len(b_src_ok),
        rate_b_person=rate(len(b_src_ok), len(b_src)),
        a_uniq_reg=len(set(c['entered'] for c in a if c['ok'])),
        b_uniq_reg=len(set(c['entered'] for c in b if c['ok'])),
        uniq_reg=len(set(c['entered'] for c in okc)),
        rate_all=rate(len(okc), total), rate_nz=rate(len(okc), len(nz)),
    )


def select(calls, start, end, day_type='all', exclude_dates=(), test_sources=()):
    """集計対象の切り分け。returns: dict of call lists"""
    excl = set(exclude_dates)
    test = set(digits(s) for s in test_sources if s)
    period = [c for c in calls
              if start <= c['date'] <= end and day_type_match(c['date'], day_type)]
    anon = [c for c in period if c['rt'] == 'anon']
    bot = [c for c in period if c['src'] in test]
    main = [c for c in period if c['rt'] != 'anon' and c['src'] not in test]
    return dict(period=period, anon=anon, bot=bot, main=main,
                base=[c for c in main if c['date'] not in excl])


def dropouts(calls, start, end, test_sources=()):
    """離脱者（Step "1-7" の登録 webhook が成立しなかった着信）を時刻順で返す。

    母集団はレポートの離脱数と同じ主集計（A+B・テスト発信元を除外）。
    非通知は発信元が残らず架電できないため主集計と同様に対象外。
    異常日（--exclude-dates）は架電対象としては残るため含める。
    """
    s = select(calls, start, end, 'all', (), test_sources)
    return [c for c in s['main'] if not c['ok']]


def aggregate(calls, meta, start, end, day_type='all',
              exclude_dates=(), test_sources=(), missing_dates=()):
    """レポート描画用の集計辞書を返す。"""
    excl = set(exclude_dates)
    missing = set(missing_dates)
    s = select(calls, start, end, day_type, excl, test_sources)
    period, anon_calls, bot_calls = s['period'], s['anon'], s['bot']
    main_calls, base = s['main'], s['base']

    out = dict(period=dict(start=start, end=end), exclude_dates=sorted(excl),
               day_type=day_type, missing_dates=sorted(missing),
               source=dict(files=[str(p) for p in meta['files']],
                           rows=meta['rows'], dup_removed=meta['dup_removed'],
                           scenarios=meta['scenarios'],
                           log_first=meta['first'], log_last=meta['last']))
    out['total'] = block(base)             # 主指標（平常ベース）
    out['total_incl'] = block(main_calls)  # 異常日込み（参考）

    # ---- 異常日の内訳 ----
    anomalies = []
    for d in sorted(excl):
        sub = [c for c in main_calls if c['date'] == d]
        if not sub:
            continue
        okc = [c for c in sub if c['ok']]
        hh = Counter(c['hour'] for c in sub)
        hh_ok = Counter(c['hour'] for c in okc)
        anomalies.append(dict(
            date=d, wd=WD[datetime.strptime(d, '%Y-%m-%d').weekday()],
            **{f'b_{k}': v for k, v in block(sub).items()},
            hourly=[dict(hour=h, calls=hh.get(h, 0), ok=hh_ok.get(h, 0))
                    for h in range(24) if hh.get(h, 0)],
            daytime=sum(v for h, v in hh.items() if 9 <= h < 18),
            top_srcs=Counter(c['src'] for c in sub).most_common(5),
            med_sec=sorted(c['sec'] for c in sub)[len(sub) // 2],
        ))
    out['anomalies'] = anomalies

    # ---- テストトラフィック（非通知 + 指定発信元・別掲） ----
    an_ok = [c for c in anon_calls if c['ok']]
    ce_anon = Counter(c['entered'] for c in an_ok)
    secs = sorted(c['sec'] for c in an_ok) or [0]
    anon_stats = dict(
        calls=len(anon_calls), ok=len(an_ok), uniq_nums=len(ce_anon),
        night_share=rate(sum(1 for c in anon_calls if 1 <= c['hour'] <= 6), len(anon_calls)),
        first=min((c['date'] for c in an_ok), default=None),
        last=max((c['date'] for c in an_ok), default=None),
        sec_min=secs[0], sec_med=secs[len(secs) // 2], sec_max=secs[-1],
        monthly=Counter(c['date'][:7] for c in an_ok).most_common(),
    )
    sources = []
    for src in sorted(set(digits(x) for x in test_sources if x)):
        sub = [c for c in bot_calls if c['src'] == src]
        if not sub:
            continue
        okc = [c for c in sub if c['ok']]
        ss = sorted(c['sec'] for c in okc) or [0]
        sources.append(dict(
            src=src, calls=len(sub), ok=len(okc),
            uniq_nums=len(set(c['entered'] for c in okc)),
            days=len(set(c['date'] for c in sub)),
            first=min(c['date'] for c in sub), last=max(c['date'] for c in sub),
            sec_med=ss[len(ss) // 2],
        ))
    test_ok = an_ok + [c for c in bot_calls if c['ok']]
    ce_all = Counter(c['entered'] for c in test_ok)
    main_reg = set(c['entered'] for c in main_calls if c['ok'])
    bot_nums = set(c['entered'] for c in bot_calls if c['ok'])
    out['test'] = dict(
        anon=anon_stats, sources=sources,
        calls=len(anon_calls) + len(bot_calls), ok=len(test_ok),
        uniq_nums=len(ce_all),
        repeats=[[k, v] for k, v in ce_all.most_common() if v > 1],
        singles=sum(1 for v in ce_all.values() if v == 1),
        overlap_anon_src=len(set(ce_anon) & bot_nums),
        overlap_main_reg=len(set(ce_all) & main_reg),
    )

    # ---- 日別（暦日・A+B。異常日もチャート用に含め excluded フラグを付与） ----
    d0 = datetime.strptime(start, '%Y-%m-%d')
    d1 = datetime.strptime(end, '%Y-%m-%d')
    days, cur = [], d0
    while cur <= d1:
        ds = cur.strftime('%Y-%m-%d')
        if day_type_match(ds, day_type):
            days.append(dict(date=ds, wd=WD[cur.weekday()], excluded=ds in excl,
                             missing=ds in missing,
                             **block([c for c in main_calls if c['date'] == ds])))
        cur += timedelta(days=1)
    out['daily'] = days
    out['day_count'] = sum(1 for d in days if not d['missing'])

    bdays = [d for d in days if not d['excluded'] and not d['missing']]
    n = len(bdays)

    def avg(key):
        return round(sum(d[key] for d in bdays) / n, 1) if n else 0
    out['daily_avg'] = dict(
        calls=avg('calls'), calls_nz=avg('calls_nz'), ok=avg('ok'),
        a_calls=avg('a_calls'), b_calls=avg('b_calls'),
        a_ok=avg('a_ok'), b_ok=avg('b_ok'), uniq_reg=avg('uniq_reg'),
        b_persons=avg('b_persons'), b_persons_ok=avg('b_persons_ok'),
        rate_all=rate(sum(d['ok'] for d in bdays), sum(d['calls'] for d in bdays)),
        rate_nz=rate(sum(d['ok'] for d in bdays), sum(d['calls_nz'] for d in bdays)),
        rate_b_person=rate(sum(d['b_persons_ok'] for d in bdays),
                           sum(d['b_persons'] for d in bdays)),
        n_days=n,
    )

    # ---- 月別サマリ（異常日込み + 除外版） ----
    months = sorted({dd['date'][:7] for dd in days})
    monthly = []
    if len(months) > 1:
        for m in months:
            mc = [c for c in main_calls if c['date'][:7] == m]
            entry = dict(month=m, days=sum(1 for dd in days if dd['date'][:7] == m),
                         **block(mc))
            m_excl = [d for d in excl if d.startswith(m) and day_type_match(d, day_type)]
            m_miss = [d for d in missing if d.startswith(m) and day_type_match(d, day_type)]
            if m_excl or m_miss:
                entry['base'] = block([c for c in mc if c['date'] not in excl])
                entry['base_days'] = entry['days'] - len(m_excl) - len(m_miss)
            monthly.append(entry)
    out['monthly'] = monthly

    # ---- 夜間シフト（D 20:00〜D+1 7:59・A+B 全日） ----
    shifts = [dict(date=d['date'], wd=d['wd'], missing=d['missing'],
                   **block([c for c in main_calls if c['shift'] == d['date']]))
              for d in days]
    out['shifts'] = shifts
    sd = [s for s in shifts if not s['missing']]  # 異常日は含める（昼スパイクはシフト窓外）
    ns = len(sd)
    out['shift_avg'] = dict(
        calls=round(sum(s['calls'] for s in sd) / ns, 1) if ns else 0,
        ok=round(sum(s['ok'] for s in sd) / ns, 1) if ns else 0,
        uniq_reg=round(sum(s['uniq_reg'] for s in sd) / ns, 1) if ns else 0,
        rate_all=rate(sum(s['ok'] for s in sd), sum(s['calls'] for s in sd)),
    )

    # ---- 時間帯別（平常ベース・稼働順） ----
    hourly = []
    for hh in list(range(20, 24)) + list(range(0, 20)):
        sub = [c for c in base if c['hour'] == hh]
        b = block(sub)
        hourly.append(dict(hour=hh, **b,
                           avg_calls=round(len(sub) / n, 1) if n else 0,
                           avg_ok=round(b['ok'] / n, 1) if n else 0))
    out['hourly'] = hourly

    # ---- 時間グループ（平常ベース） ----
    def grp(name, pred, note=''):
        return dict(name=name, note=note, **block([c for c in base if pred(c['hour'])]))
    out['groups'] = [
        grp('IVR稼働帯 20:00〜翌7:59', lambda h: h >= 20 or h < 8, '定義'),
        grp('その他 8:00〜19:59', lambda h: 8 <= h < 20, '定義外'),
        grp('参考: 実測稼働窓 19:00〜翌8:59', lambda h: h >= 19 or h < 9, 'ログ実測'),
    ]

    # ---- 全体ユニークのレンジ推定（平常ベース・参考） ----
    all_reg = set(c['entered'] for c in base if c['ok'])
    b_src = set(c['src'] for c in base if c['rt'] == 'B')
    ident = b_src | all_reg
    a_unid = sum(1 for c in base if c['rt'] == 'A' and not c['ok'] and c['sec'] > 0)
    out['range'] = dict(
        ident=len(ident), b_src=len(b_src), reg=len(all_reg),
        overlap=len(b_src & all_reg), a_unid_calls=a_unid,
        lo=len(ident), hi=len(ident) + a_unid,
        rate_lo=rate(len(all_reg), len(ident) + a_unid),
        rate_hi=rate(len(all_reg), len(ident)),
    )

    # ---- 経路跨ぎ（平常ベース） ----
    a_reg = set(c['entered'] for c in base if c['rt'] == 'A' and c['ok'])
    b_reg = set(c['entered'] for c in base if c['rt'] == 'B' and c['ok'])
    out['cross'] = dict(reg_both=len(a_reg & b_reg), a_reg_in_b_src=len(a_reg & b_src))

    # ---- 経路別サマリ（平常ベース） ----
    routes = {}
    for rt in ('A', 'B'):
        sub = [c for c in base if c['rt'] == rt]
        okc = [c for c in sub if c['ok']]
        zero = sum(1 for c in sub if c['sec'] == 0)
        routes[rt] = dict(
            calls=len(sub), zero=zero, ok=len(okc),
            rate_all=rate(len(okc), len(sub)), rate_nz=rate(len(okc), len(sub) - zero),
            src_count=len(set(c['src'] for c in sub)),
            uniq_reg=len(set(c['entered'] for c in okc)),
        )
    out['routes'] = routes

    # ---- リピート分析（平常ベース） ----
    cc = Counter(c['src'] for c in base)
    okc = [c for c in base if c['ok']]
    per_caller = defaultdict(set)
    for c in okc:
        per_caller[c['src']].add(c['entered'])
    ent = Counter(c['entered'] for c in okc)
    multi_ent = {k: v for k, v in ent.items() if v > 1}
    b_cc = Counter(c['src'] for c in base if c['rt'] == 'B')
    out['repeat'] = dict(
        calls_top=cc.most_common(5),
        trunk_like=sorted(((k, len(v)) for k, v in per_caller.items() if len(v) > 1),
                          key=lambda x: -x[1])[:6],
        reg_numbers_multi=len(multi_ent),
        reg_dup_records=sum(multi_ent.values()) - len(multi_ent),
        s16_not_ok=sum(1 for c in base if c['s16'] and not c['ok']),
        b_repeat_callers=sum(1 for v in b_cc.values() if v > 1),
        b_max_calls=max(b_cc.values()) if b_cc else 0,
    )

    # ---- ファネル（平常ベース・CSV の列順＝シナリオ順） ----
    reached = Counter()
    for c in base:
        for name in c['reached']:
            reached[name] += 1
    out['funnel'] = [dict(step=name, reached=reached.get(name, 0),
                          share=rate(reached.get(name, 0), len(base)))
                     for name in meta['step_names']]

    # ---- 離脱の内訳（平常ベース） ----
    dr = [c for c in base if not c['ok']]
    out['dropout'] = dict(
        calls=len(dr), share=rate(len(dr), len(base)),
        by_last_step=Counter(c['last_step'] for c in dr).most_common(),
        by_route={'A': sum(1 for c in dr if c['rt'] == 'A'),
                  'B': sum(1 for c in dr if c['rt'] == 'B')},
        by_kind=Counter(c['kind'] for c in dr).most_common(),
        reachable=sum(1 for c in dr if c['rt'] == 'B'),
        sec_buckets=Counter(
            '0秒' if c['sec'] == 0 else '1-9秒' if c['sec'] < 10
            else '10-29秒' if c['sec'] < 30 else '30-59秒' if c['sec'] < 60 else '60秒+'
            for c in dr).most_common(),
    )

    # ---- 品質ノート ----
    out['quality'] = dict(
        zero_sec=sum(1 for c in base if c['sec'] == 0),
        bad_entered=[c['entered'] for c in okc if len(c['entered']) not in (10, 11)],
    )
    return out
