#!/usr/bin/env python3
"""集計結果から Markdown レポートを生成する。

Slack・Confluence・チケットにそのまま貼れる長さに絞り、HTML レポートの
主要指標（KPI・経路別・日別・時間帯別）に離脱の内訳を加えた構成にする。
"""
from datetime import date

from holidays import names_in_range

A_SHORT, B_SHORT = '親番号媒体', '子番号直着信'


def _n(v):
    return '–' if v is None else f'{v:,}' if isinstance(v, int) else f'{v}'


def _p(v):
    return '–' if v is None else f'{v}%'


def _tel(s):
    if not s:
        return '(非通知)'
    if len(s) == 11:
        return f'{s[:3]}-{s[3:7]}-{s[7:]}'
    if len(s) == 10:
        return f'{s[:4]}-{s[4:7]}-{s[7:]}'
    return s


def _table(head, rows, align=None):
    align = align or ['---'] * len(head)
    out = ['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join(align) + ' |']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


R = ['---:'] * 8


def render(data, sub_label='', top_days=0):
    """data = {'all': 集計dict, 'weekday': ..., 'holiday': ...} → Markdown 文字列"""
    D = data['all']
    p, t, avg = D['period'], D['total'], D['daily_avg']
    src = D.get('source', {})
    rt, dr = D['routes'], D['dropout']
    title = f'IVR 受電 × 電話番号登録 レポート{f"（{sub_label}）" if sub_label else ""}'

    L = [f'# {title}', '']
    L.append(f'- 対象期間: **{p["start"]} 〜 {p["end"]}**（{D["day_count"]} 日）')
    L.append(f'- データ: IVRコールログCSV {len(src.get("files", []))} ファイル / '
             f'{_n(src.get("rows", 0))} 行'
             + (f'（ID重複 {_n(src["dup_removed"])} 行を排除）' if src.get('dup_removed') else ''))
    L.append(f'- 登録の定義: Step "1-7" 電話番号通知 webhook が `200 / result=OK`')
    L.append(f'- 作成: {date.today():%Y-%m-%d}')
    hs = names_in_range(p['start'], p['end'])
    if hs:
        L.append('- ⚠ 期間内に祝日あり: ' + '／'.join(f'{d[5:].replace("-", "/")} {n}' for d, n in hs))
    L.append('')

    # ---- サマリ ----
    L += ['## サマリ', '',
          _table(['指標', '値', '補足'],
                 [['受電数（実顧客・A+B）', _n(t['calls']), f'0秒除外 {_n(t["calls_nz"])} / 日平均 {avg["calls"]}'],
                  ['電話番号登録数', _n(t['ok']), f'日平均 {avg["ok"]}'],
                  ['**登録率（全着信）**', f'**{_p(t["rate_all"])}**', f'0秒除外ベース {_p(t["rate_nz"])}'],
                  ['ユニーク登録人数', _n(t['uniq_reg']), '1-6 入力番号で重複排除'],
                  ['**離脱数（登録に至らず）**', f'**{_n(dr["calls"])}**', f'離脱率 {_p(dr["share"])}'],
                  ['　うち折り返し架電が可能', _n(dr['reachable']),
                   f'発信元が顧客番号（B経路）の分。A経路 {_n(dr["by_route"]["A"])} 件は発信元が媒体FDのため不可'],
                  ], ['---', '---:', '---']), '']

    # ---- タブ別 ----
    L += ['## 全体 / 平日 / 休日', '',
          _table(['区分', '日数', '受電数', '登録数', '登録率', '日平均受電', '離脱数'],
                 [[lbl, data[k]['day_count'], _n(data[k]['total']['calls']),
                   _n(data[k]['total']['ok']), _p(data[k]['total']['rate_all']),
                   data[k]['daily_avg']['calls'], _n(data[k]['dropout']['calls'])]
                  for k, lbl in (('all', '全体'), ('weekday', '平日（月〜金・祝日除く）'),
                                 ('holiday', '休日（土日祝）'))],
                 ['---'] + R[:6]), '']

    # ---- 経路別 ----
    L += ['## 経路別', '',
          f'発信元が `0120` / `0800` の着信を **A: {A_SHORT}**（CTI 経由・発信元は媒体のフリーダイヤル＝人物特定不可）、',
          f'それ以外の発信元通知ありを **B: {B_SHORT}**（顧客番号が透過＝ほぼ本人番号）として分ける。', '',
          _table(['', f'A: {A_SHORT}', f'B: {B_SHORT}'],
                 [['受電数', _n(rt['A']['calls']), _n(rt['B']['calls'])],
                  ['0秒切断', _n(rt['A']['zero']), _n(rt['B']['zero'])],
                  ['登録数', _n(rt['A']['ok']), _n(rt['B']['ok'])],
                  ['登録率（全着信）', _p(rt['A']['rate_all']), _p(rt['B']['rate_all'])],
                  ['登録率（0秒除外）', _p(rt['A']['rate_nz']), _p(rt['B']['rate_nz'])],
                  ['ユニーク登録', _n(rt['A']['uniq_reg']), _n(rt['B']['uniq_reg'])],
                  ['発信元番号の種類数', _n(rt['A']['src_count']), _n(rt['B']['src_count'])]],
                 ['---', '---:', '---:']), '']
    if t['b_persons']:
        L += [f'B経路の人物ベース: 受電 {_n(t["b_persons"])} 人 → 登録 {_n(t["b_persons_ok"])} 人 '
              f'（**{_p(t["rate_b_person"])}**）', '']

    # ---- ファネル ----
    fn = [f for f in D['funnel'] if f['reached']]
    if fn:
        L += ['## シナリオ到達（平常ベース・CSVのステップ列順）', '',
              _table(['ステップ', '到達数', '対受電'],
                     [[f['step'], _n(f['reached']), _p(f['share'])] for f in fn],
                     ['---', '---:', '---:']), '']

    # ---- 離脱 ----
    L += ['## 離脱の内訳', '',
          f'離脱 = Step "1-7" の登録 webhook が成立しなかった着信。{_n(dr["calls"])} 件（受電の {_p(dr["share"])}）。', '',
          '### 最終到達ステップ', '',
          _table(['最後に到達したステップ', '件数'],
                 [[k, _n(v)] for k, v in dr['by_last_step']], ['---', '---:']), '',
          '### 発信元番号の種別（折り返し架電の可否）', '',
          _table(['種別', '件数', '架電'],
                 [[k, _n(v), '不可（媒体FD）' if k == 'フリーダイヤル'
                   else '不可' if k == '非通知' else '可'] for k, v in dr['by_kind']],
                 ['---', '---:', '---']), '',
          '### 通話秒数', '',
          _table(['秒数', '件数'], [[k, _n(v)] for k, v in dr['sec_buckets']], ['---', '---:']), '']

    # ---- 時間帯 ----
    L += ['## 時間帯別（平常ベース・稼働順 20時→翌19時）', '',
          _table(['時間帯', '受電数', f'内A', f'内B', '日平均', '登録数', '登録率'],
                 [[f'{h["hour"]:02d}:00〜{h["hour"]:02d}:59', _n(h['calls']), _n(h['a_calls']),
                   _n(h['b_calls']), h['avg_calls'], _n(h['ok']), _p(h['rate_all'])]
                  for h in D['hourly'] if h['calls']],
                 ['---'] + R[:6]), '',
          _table(['時間グループ', '受電数', '登録数', '登録率'],
                 [[g['name'], _n(g['calls']), _n(g['ok']), _p(g['rate_all'])] for g in D['groups']],
                 ['---'] + R[:3]), '']

    # ---- 日別 ----
    days = [d for d in D['daily'] if not d['missing']]
    shown = days[-top_days:] if top_days and len(days) > top_days else days
    L += ['## 日別推移（暦日ベース）', '']
    if len(shown) < len(days):
        L.append(f'（直近 {len(shown)} 日を表示。全 {len(days)} 日は HTML / CSV を参照）')
        L.append('')
    L += [_table(['日付', '受電数', '内A', '内B', '登録数', '登録率', 'ユニーク登録'],
                 [[f'{d["date"][5:]} ({d["wd"]})' + ('　※異常日' if d['excluded'] else ''),
                   _n(d['calls']), _n(d['a_calls']), _n(d['b_calls']), _n(d['ok']),
                   _p(d['rate_all']), _n(d['uniq_reg'])] for d in shown],
                 ['---'] + R[:6]), '',
          f'日平均: 受電 {avg["calls"]} / 登録 {avg["ok"]} / 登録率 {_p(avg["rate_all"])}'
          f'（{avg["n_days"]} 日ベース）', '']

    # ---- 夜間シフト ----
    sa = D['shift_avg']
    L += ['## 夜間シフト単位（20:00〜翌7:59 を開始日に帰属）', '',
          'IVR の稼働は日を跨ぐため、暦日集計では 1 夜が 2 日に分割される。'
          'この表は 1 夜を 1 行に再集計したもの。', '',
          f'シフト平均: 受電 {sa["calls"]} / 登録 {sa["ok"]} / 登録率 {_p(sa["rate_all"])}', '']

    # ---- テスト・非通知 ----
    te = D['test']
    if te['calls']:
        an = te['anon']
        L += ['## 主集計から分離したトラフィック', '',
              f'- 非通知: {_n(an["calls"])} 件（うち登録 {_n(an["ok"])} 件・ユニーク番号 {_n(an["uniq_nums"])}）',
              ]
        for s in te['sources']:
            L.append(f'- テスト発信元 {_tel(s["src"])}: {_n(s["calls"])} 件'
                     f'（登録 {_n(s["ok"])} 件・{_n(s["days"])} 日にわたる）')
        L.append('')

    # ---- 品質 ----
    q = D['quality']
    L += ['## データ品質・注意事項', '',
          f'- 通話0秒の着信 {_n(q["zero_sec"])} 件（IVR応答前の切断。1-6 入力は未完了）',
          f'- 1-6 入力番号の形式異常 {len(q["bad_entered"])} 件'
          + ('（' + ', '.join(q['bad_entered'][:5]) + '）' if q['bad_entered'] else ''),
          '- 平日/休日は着信のカレンダー日付で判定。IVR夜間帯は日跨ぎのため、'
          '月曜0〜8時の着信（日曜夜シフトの後半）は平日側に含まれる。',
          ]
    if D['exclude_dates']:
        L.append(f'- 異常日として平常ベースから除外: {", ".join(D["exclude_dates"])}')
    if D['missing_dates']:
        L.append(f'- データ欠測日（日数分母から除外）: {", ".join(D["missing_dates"])}')
    L.append('')
    return '\n'.join(L)
