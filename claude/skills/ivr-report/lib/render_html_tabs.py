#!/usr/bin/env python3
"""集計結果（全体／平日／休日）からタブ切替式の自己完結型 HTML レポートを生成する。

チャート・テーブル・CSS の共有部品は render_html.py から import する。
経路の呼称:
  A = 親番号媒体（CTI 経由・発信元は媒体のフリーダイヤル）
  B = 子番号直着信（顧客番号透過）

B 経路が僅少（平常ベースの B 受電が閾値未満）のときは、B 人物ファネル・
レンジ推定セクションを算出対象外の注記に置き換える。
"""
import json
import sys
from datetime import date

from holidays import names_in_range
from datetime import datetime

from render_html import (
    fmt, pct, tel, daily_chart, hourly_chart, row_cells,
    daily_table, shift_table, hourly_table, group_table, anomaly_section,
    b_funnel_table, CSS,
)

B_DEGENERATE_THRESHOLD = 50

A_TITLE, A_SUB = 'A: 親番号媒体', 'CT-e1経由・発信元は媒体のフリーダイヤル'
B_TITLE, B_SUB = 'B: 子番号直着信', '顧客番号透過'
A_SHORT, B_SHORT = '親番号媒体', '子番号直着信'
A_CHART_LABEL, B_CHART_LABEL = 'A(親番号媒体)', 'B(子番号直着信)'

DAY_BOUNDARY_NOTE = (
    '平日/休日は着信のカレンダー日付で判定。IVR夜間帯は日跨ぎのため、'
    '例: 月曜0〜8時の着信（日曜夜シフトの後半）は平日側に含まれる。'
)

DEGENERATE_NOTE = (
    'B経路（顧客番号透過）の着信が僅少のため人物ファネルは算出対象外。'
    '全着信がCT-e1経由（発信元=媒体フリーダイヤル）のため、人数の識別は1-6入力番号でのみ可能。'
)

TAB_LABELS = dict(all='全体', weekday='平日（月〜金・祝日除く）', holiday='休日（土日祝）')

TAB_HEAD = f'''<tr>
<th></th><th>受電数<br><span>A+B</span></th><th>内A<br><span>{A_SHORT}</span></th><th>内B<br><span>{B_SHORT}</span></th>
<th>受電数<br><span>0秒除外</span></th>
<th>登録数<br><span>1-7 OK</span></th><th>内A</th><th>内B</th>
<th>登録率<br><span>/全着信</span></th><th>登録率<br><span>/0秒除外</span></th>
<th>ﾕﾆｰｸ登録<br><span>入力番号</span></th>
</tr>'''

TAB_HOURLY_HEAD = f'''<tr>
<th>時間帯</th><th>受電数<br><span>期間合計</span></th><th>内A<br><span>{A_SHORT}</span></th><th>内B<br><span>{B_SHORT}</span></th>
<th>受電数<br><span>日平均</span></th><th>受電数<br><span>0秒除外</span></th>
<th>登録数<br><span>期間合計</span></th><th>内A</th><th>内B</th><th>登録数<br><span>日平均</span></th>
<th>登録率<br><span>/全着信</span></th><th>登録率<br><span>/0秒除外</span></th>
</tr>'''
TAB_HOURLY_NOTE = '平常ベース（異常日除外）。受電0件の時間帯は行を省略。グレー行はIVR稼働時間外（ただし着信実績あり）。'


def safe_pct(n, d, decimals=0):
    """d==0 でも例外/NaN/Infinityを出さない百分率フォーマッタ。"""
    if not d:
        return '–'
    return f'{100.0*n/d:.{decimals}f}%'


def range_pct(v):
    return f'{v:.0f}%' if v is not None else '–'


def is_degenerate_b(D):
    return D['total']['b_calls'] < B_DEGENERATE_THRESHOLD


def format_missing_note(missing_dates):
    if not missing_dates:
        return None
    dts = sorted(datetime.strptime(d, '%Y-%m-%d') for d in missing_dates)
    contiguous = len(dts) > 1 and all((dts[i + 1] - dts[i]).days == 1 for i in range(len(dts) - 1))
    if contiguous:
        label = f"{dts[0].strftime('%-m/%-d')}〜{dts[-1].strftime('%-m/%-d')}"
    else:
        label = '・'.join(d.strftime('%-m/%-d') for d in dts)
    return f'{label} はデータ0件（エクスポート欠落疑い・要確認）。日次平均の分母から除外。'


# ---------- 経路別サマリ（新表記） ----------
def route_compare_table_v2(D, degrade_b):
    A, B = D['routes']['A'], D['routes']['B']
    t = D['total']
    b_funnel_cell = (
        f'<b>受電 {fmt(t["b_persons"])} 人 → 登録 {fmt(t["b_persons_ok"])} 人 = {pct(t["rate_b_person"])}</b>'
        if not degrade_b else '算出対象外（僅少）'
    )
    return f'''<table class="routecmp">
<tr><th></th><th>{A_TITLE}<br><span>{A_SUB}</span></th><th>{B_TITLE}<br><span>{B_SUB}</span></th></tr>
<tr><td class="lbl">発信元番号の意味</td><td>媒体のフリーダイヤル（0120/0800・{A["src_count"]}本）<br><b>人物特定不可（CT-e1経由）</b></td><td>顧客番号がそのまま透過<br><b>ほぼ本人の番号</b></td></tr>
<tr><td class="lbl">受電数</td><td>{fmt(A["calls"])} 件（{safe_pct(A["calls"], t["calls"])}）</td><td>{fmt(B["calls"])} 件（{safe_pct(B["calls"], t["calls"])}）</td></tr>
<tr><td class="lbl">0秒切断</td><td>{fmt(A["zero"])} 件（{safe_pct(A["zero"], A["calls"])}）転送リトライ由来か</td><td>{fmt(B["zero"])} 件（{safe_pct(B["zero"], B["calls"])}）</td></tr>
<tr><td class="lbl">登録数（1-7 OK）</td><td class="ok">{fmt(A["ok"])} 件</td><td class="ok">{fmt(B["ok"])} 件</td></tr>
<tr><td class="lbl">登録率（全数 / 0秒除外）</td><td class="rate">{pct(A["rate_all"])} / {pct(A["rate_nz"])}</td><td class="rate">{pct(B["rate_all"])} / {pct(B["rate_nz"])}</td></tr>
<tr><td class="lbl">ユニーク登録人数（入力番号）</td><td class="ok">{fmt(A["uniq_reg"])} 人</td><td class="ok">{fmt(B["uniq_reg"])} 人</td></tr>
<tr><td class="lbl">人物ファネル</td><td>算出不能（分母の人数が不明）</td><td class="hl">{b_funnel_cell}</td></tr>
</table>'''


def route_section(D, degrade_b):
    R, t = D['routes'], D['total']
    lede = (DEGENERATE_NOTE if degrade_b else
            f'「受電した人のうち登録してくれた人の割合」として最も信頼できるのは <b>{B_TITLE}の人物登録率 {pct(t["rate_b_person"])}</b>。')
    parts = [f'''<h2>経路別サマリ — {A_TITLE} と {B_TITLE} は別物（平常ベース）</h2>
<p class="desc">発信元 0120/0800 = 媒体（CT-e1）側のフリーダイヤルからの着信（A）と判定。</p>
{route_compare_table_v2(D, degrade_b)}
<div class="info">💡 <b>読み方</b>: {lede}
{A_CHART_LABEL}はコールベースの登録率（{pct(R["A"]["rate_all"])}、0秒除外 {pct(R["A"]["rate_nz"])}）と登録人数 {fmt(t["a_uniq_reg"])} 人のみ追跡。
{A_CHART_LABEL}の0秒切断率 {safe_pct(R["A"]["zero"], R["A"]["calls"])} はCT-e1側の品質指標として別途監視する価値がある。</div>''']
    if degrade_b:
        parts.append(f'<h3>B経路の人物ファネル・レンジ推定</h3>\n<div class="info">ℹ️ {DEGENERATE_NOTE}</div>')
    else:
        rg, cx = D['range'], D['cross']
        parts.append(f'''<h3>B経路の人物ファネル（日別）＋ 登録人数</h3>
{b_funnel_table(D)}
<h3>全体ユニーク登録率のレンジ推定（参考②・平常ベース）</h3>
<ul class="plain">
<li>識別可能人物 = B発信元 {fmt(rg["b_src"])} 人 ∪ 登録入力番号 {fmt(rg["reg"])} 人（重複 {fmt(rg["overlap"])}）= <b>{fmt(rg["ident"])} 人（下限）</b></li>
<li>上限 = 下限 + A経路の未登録・0秒超コール {fmt(rg["a_unid_calls"])} 件を「1コール=1人」とみなす = <b>{fmt(rg["hi"])} 人</b></li>
<li>→ ユニーク受電 {fmt(rg["lo"])}〜{fmt(rg["hi"])} 人、<b>ユニーク登録率 {range_pct(rg["rate_lo"])}〜{range_pct(rg["rate_hi"])}</b>（真値はこの間。B実測 {pct(t["rate_b_person"])} とも整合）</li>
<li>経路跨ぎはごく僅か: 両経路で登録された番号 {cx["reg_both"]} 件、A経路で登録された番号がB経路の発信元にも出現 {cx["a_reg_in_b_src"]} 件</li>
</ul>''')
    return '\n'.join(parts)


# ---------- テストトラフィック分離（完全データ駆動・特定日/特定%のハードコード無し） ----------
def test_section_v2(D):
    te = D['test']
    an = te['anon']
    if not an['calls'] and not te['sources']:
        return ''  # このビューには分離対象トラフィックが無い
    rep_rows = ''.join(
        f'<tr><td class="lbl">{k[:4]}-{k[4:7]}-{k[7:] if len(k) >= 10 else k}</td><td>{v}</td></tr>'
        for k, v in te['repeats'][:24])
    more = len(te['repeats']) - 24
    monthly = ' ／ '.join(f'{int(m[0][5:7])}月 {m[1]}件' for m in an['monthly'])
    src_rows = ''.join(
        f'''<tr><td class="lbl">{tel(s["src"])}</td><td>{fmt(s["calls"])}</td><td class="ok">{fmt(s["ok"])}</td>
<td>{fmt(s["uniq_nums"])}</td><td>{s["days"]}日</td><td class="lbl" style="font-weight:400">{s["first"][5:]}〜{s["last"][5:]}</td></tr>'''
        for s in te['sources'])
    b_ok = D['routes']['B']['ok']
    bot_ok = sum(s['ok'] for s in te['sources'])
    inflate_pct = safe_pct(bot_ok, b_ok + bot_ok, 0)
    anon_block = (
        f'''<li>登録率 {safe_pct(an["ok"], an["calls"])} は実顧客としては不自然に高い。初出 {an["first"]} 〜 最終 {an["last"]}。</li>
<li>着信の {pct(an["night_share"])} が深夜1〜6時に集中。通話秒数 {an["sec_min"]}〜{an["sec_max"]}秒（中央値 {an["sec_med"]}秒）に均一で<b>スクリプト的</b>。</li>'''
        if an['ok'] else
        ('<li>この期間・このビューの非通知は登録0件で、テスト痕跡は見られない。識別不能のため方針通り主集計から分離のみ行う。</li>'
         if an['calls'] else '<li>この期間・このビューには非通知の着信自体がない。</li>')
    )
    # 入れ子の三重引用符 f-string は Python 3.12 未満で解釈できないため変数に切り出す
    if te['sources']:
        src_block = (
            f'<table><tr><th>発信元</th><th>コール</th><th>登録</th>'
            f'<th>登録番号数</th><th>稼働</th><th>期間</th></tr>{src_rows}</table>\n'
            f'<ul class="plain" style="margin-top:8px;">\n'
            f'<li>約90秒間隔の機械的発信・通話秒数均一。<b>非通知テストと同一の番号群を登録</b>'
            f'（共通 {te["overlap_anon_src"]} 番号）しており同一のテスト運用と判断。</li>\n'
            f'<li>分離しない場合、{B_TITLE}の登録数を約{inflate_pct}過大計上する'
            f'（このビュー内のテスト登録 {fmt(bot_ok)} 件）。</li>\n</ul>')
    else:
        src_block = '<p class="note">この期間・このビューにはテスト発信元の活動なし。</p>'

    return f'''<section>
<h2>テスト疑いトラフィック（主集計から分離）</h2>
<p class="desc">分離対象 = ①非通知の全着信 ＋ ②特定発信元（下表）。合計 {fmt(te["calls"])} 件・登録 {fmt(te["ok"])} 件を実顧客の集計から除外している。</p>
<div class="cols2">
<div>
<b style="font-size:12.5px;">① 非通知（{fmt(an["calls"])}件・登録 {fmt(an["ok"])}件{f": {monthly}" if monthly else ""}）</b>
<ul class="plain">
{anon_block}
</ul>
<b style="font-size:12.5px;">② テスト発信元（発信元番号つきのボット）</b>
{src_block}
<b style="font-size:12.5px;">判定の根拠まとめ</b>
<ul class="plain">
<li>テストの登録番号 {fmt(te["uniq_nums"])} 種と実顧客(A+B)の登録番号の重複は <b>{te["overlap_main_reg"]} 件</b> — 番号空間が完全に分離しており誤除外の心配は小さい。</li>
<li>単発登録 {fmt(te["singles"])} 番号には本物の非通知顧客が混在する可能性は残る。</li>
</ul>
</div>
<div>
<b style="font-size:12.5px;">反復登録された番号（上位24／全{len(te["repeats"])}件）</b>
{f'<table><tr><th>登録された番号</th><th>回数</th></tr>{rep_rows}</table>' if te['repeats'] else '<p class="note">反復登録された番号はこのビューにはない。</p>'}
{f'<p class="note">他 {more} 番号は JSON 出力の test.repeats 参照。</p>' if more > 0 else ''}
</div>
</div>
</section>'''


# ---------- リピート・重複／データ品質（新表記・全テナントで成立する記述のみ） ----------
def repeat_section(D):
    r, t = D['repeat'], D['total']
    top_callers = ''.join(f'<tr><td class="lbl">{tel(c[0])}</td><td>{fmt(c[1])}</td></tr>' for c in r['calls_top'])
    trunk_rows = ''.join(f'<tr><td class="lbl">{tel(c[0])}</td><td>{c[1]}</td></tr>' for c in r['trunk_like'])
    top_all_a = bool(r['calls_top']) and all(c[0].startswith(('0120', '0800')) for c in r['calls_top'])
    trunk_note = ('同一発信元から複数人の登録がある（右下表）＝ 媒体回線（0120/0800）に複数の実在顧客が合流している証拠。'
                  if r['trunk_like'] else 'この期間・このビューでは同一発信元からの複数人登録は確認されない。')
    return f'''<section>
<h2>リピート・重複の実態（平常ベース）</h2>
<div class="cols2">
<div>
<ul class="plain">
<li>登録 {fmt(t['ok'])} 件のうち同一番号の重複登録は {r['reg_numbers_multi']} 番号・{fmt(r['reg_dup_records'])} 件（{safe_pct(r['reg_dup_records'], t['ok'], 1)}）。掛け直して再登録する行動は少数。</li>
<li>{B_TITLE}(本人番号)で複数回発信した人は {fmt(r['b_repeat_callers'])}／{fmt(t['b_persons'])} 人（最大 {r['b_max_calls']} 回）。</li>
<li>発信回数上位は{'すべて' if top_all_a else '大半が'}{A_TITLE}の媒体フリーダイヤル（0120/0800・右表）。</li>
<li>{trunk_note}</li>
<li>Step "1-6" 入力完了 {fmt(t['s16'])} 件に対し webhook 発火 {fmt(t['ok'])} 件（差 {fmt(r['s16_not_ok'])} 件は入力後・1-7通知前に切電）。</li>
</ul>
</div>
<div>
<h3 style="margin-top:0;">発信回数上位</h3>
<table><tr><th>発信元番号</th><th>コール数</th></tr>{top_callers}</table>
<h3>同一発信元からの複数人登録（上位）</h3>
{f'<table><tr><th>発信元番号</th><th>異なる入力番号数</th></tr>{trunk_rows}</table>' if r['trunk_like'] else '<p class="note">該当なし。</p>'}
</div>
</div>
</section>'''


def quality_section(D):
    q, t = D['quality'], D['total']
    dup = D.get('source', {}).get('dup_removed', 0)
    dup_note = (f'<li>入力CSV間で ID が重複する行 {fmt(dup)} 件を排除済み'
                f'（月跨ぎファイルを複数指定した場合に発生する）。</li>' if dup else '')
    h8 = next(h for h in D['hourly'] if h['hour'] == 8)
    h19 = next(h for h in D['hourly'] if h['hour'] == 19)
    return f'''<section>
<h2>データ品質・注意事項</h2>
<ul class="plain">
<li>平常ベースの通話0秒着信 {fmt(q['zero_sec'])} 件（{safe_pct(q['zero_sec'], t['calls'])}）の内訳: A {fmt(t['a_zero'])} 件（A内 {safe_pct(t['a_zero'], t['a_calls'])}）／ B {fmt(t['b_zero'])} 件（B内 {safe_pct(t['b_zero'], t['b_calls'])}）。0秒着信はIVR応答前の切断であり、全て 1-6 入力未完了。</li>
<li>1-6 で入力された番号の形式異常: {len(q['bad_entered'])} 件{'' if not q['bad_entered'] else '（' + ', '.join(q['bad_entered'][:5]) + '）'}。</li>
<li>稼働帯（20時〜翌8時）の外側でも、19時台に{fmt(h19['calls'])}件・8時台に{fmt(h8['calls'])}件の着信実績あり（平常ベース）。8時台の内訳: A {fmt(h8['a_calls'])}件／B {fmt(h8['b_calls'])}件。</li>
{dup_note}
</ul>
</section>'''


def holiday_warn(D):
    """期間内の祝日を注記する。休日タブでは自明なため出さない。"""
    if D['day_type'] == 'holiday':
        return ''
    dates = {d['date'] for d in D['daily']}
    hs = [(d, n) for d, n in names_in_range(D['period']['start'], D['period']['end'])
          if d in dates]
    if not hs:
        return ''
    label = '／'.join(f'{d[5:].replace("-", "/")} {n}' for d, n in hs[:6])
    more = f' ほか{len(hs) - 6}日' if len(hs) > 6 else ''
    return (f'<div class="warn">⚠ 期間内に祝日を含む（{label}{more}）。'
            f'当該日の傾向は平常日と異なる可能性がある。</div>')


def build_kpis(D, degrade_b):
    t, ti, a, cx, rg = D['total'], D['total_incl'], D['daily_avg'], D['cross'], D['range']
    has_anomaly = bool(D['anomalies'])
    kpis = [
        (f'受電数（{"平常ベース" if has_anomaly else "実顧客"}）', fmt(t['calls']),
         f'A {fmt(t["a_calls"])} ／ B {fmt(t["b_calls"])} ・ 日平均 {fmt(a["calls"])}'
         + (f' ／ 異常日込み {fmt(ti["calls"])}' if has_anomaly else '')),
        ('電話番号登録数', fmt(t['ok']),
         f'A {fmt(t["a_ok"])} ／ B {fmt(t["b_ok"])} ・ 日平均 {fmt(a["ok"])}'
         + (f' ／ 異常日込み {fmt(ti["ok"])}' if has_anomaly else '')),
        ('登録率（全数）', pct(t['rate_all']),
         f'0秒除外 {pct(t["rate_nz"])}' + (f' ／ 異常日込み {pct(ti["rate_all"])}' if has_anomaly else '')),
    ]
    if degrade_b:
        kpis.append((f'{B_TITLE}の人物登録率', '算出対象外',
                      f'B受電僅少（{fmt(t["b_calls"])}件 < {B_DEGENERATE_THRESHOLD}）。識別は1-6入力番号のみ'))
        kpis.append(('ユニーク登録人数（1-6入力番号）', fmt(t['uniq_reg']),
                      '全着信CT-e1経由のためA/B横断のレンジ推定は対象外'
                      + (f' ／ 異常日込み {fmt(ti["uniq_reg"])}' if has_anomaly else '')))
        kpis.append(('全体ユニーク登録率', '算出対象外', 'B僅少のためレンジ推定なし。1-6入力番号でのユニーク化のみ'))
    else:
        kpis.append((f'{B_TITLE}の人物登録率 ★', pct(t['rate_b_person']),
                      f'受電 {fmt(t["b_persons"])}人 → 登録 {fmt(t["b_persons_ok"])}人'
                      + (f' ／ 込み {pct(ti["rate_b_person"])}' if has_anomaly else '')))
        kpis.append(('ユニーク登録人数', fmt(t['uniq_reg']),
                      f'A {fmt(t["a_uniq_reg"])} + B {fmt(t["b_uniq_reg"])} − 両経路重複 {cx["reg_both"]}'
                      + (f' ／ 異常日込み {fmt(ti["uniq_reg"])}' if has_anomaly else '')))
        kpis.append(('全体ユニーク登録率（参考）', f'{range_pct(rg["rate_lo"])}〜{range_pct(rg["rate_hi"])}',
                      f'ﾕﾆｰｸ受電 {fmt(rg["lo"])}〜{fmt(rg["hi"])}人のレンジ推定（A経路の未登録者数は特定不能）'))
    return kpis


def defs_box(D, degrade_b):
    has_anomaly = bool(D['anomalies'])
    excl_label = '・'.join(an['date'][5:].replace('-', '/') for an in D['anomalies'])
    uniq_note = ('<b>人ベースの登録率はB経路の人物ファネルを主指標</b>とし、全体のユニーク登録率はレンジ推定を参考値として併記'
                 if not degrade_b else
                 '<b>B経路の着信が僅少のため、1-6入力番号でのユニーク化のみで人数を把握</b>（B人物ファネル・レンジ推定は算出対象外）')
    return f'''<div class="defs">
<b>集計定義（合意済み）</b>
<ul>
<li><b>経路分類</b>: <b>{A_TITLE}</b>（{A_SUB}。人物特定不可）／ <b>{B_TITLE}</b>（{B_SUB}。発信元≒本人番号）</li>
<li><b>平日/休日の判定</b>: 着信のカレンダー日付で判定（weekday=月〜金かつ祝日でない日／holiday=土日または祝日）。{DAY_BOUNDARY_NOTE}</li>
<li><b>テストトラフィックの分離</b>: 非通知の全着信＋テスト発信元を主集計から分離し専用セクションで別掲（該当トラフィックがあるビューのみ表示）</li>
{f'<li><b>異常日の両建て</b>: 異常日（{excl_label}）を除いた「平常ベース」を主指標とし、「異常日込み」を併記。異常日単体の内訳も掲載</li>' if has_anomaly else '<li><b>異常日</b>: このビューに該当する異常日はない</li>'}
<li><b>受電数（分母）</b>: 全着信を主指標とし、通話0秒（IVR応答前切断）除外値を併記</li>
<li><b>登録数（分子）</b>: Step "1-7" webhook が <b>200 / result=OK</b>（=連携先に実登録）。Step "1-6" 入力数は参考値</li>
<li><b>同一人物のユニーク判定</b>: 登録者は入力番号でユニーク化。{uniq_note}</li>
<li><b>時間帯</b>: IVR稼働帯 20:00〜翌8:00 を1グループとしてサマリ＋1時間刻み内訳</li>
</ul>
</div>'''


def dropout_section(D):
    """離脱（登録webhookが成立しなかった着信）の内訳。離脱者CSVと同じ母集団。"""
    dr = D['dropout']
    if not dr['calls']:
        return ''
    fn = [f for f in D['funnel'] if f['reached']]
    funnel_rows = ''.join(
        f'<tr><td class="lbl">{f["step"]}</td><td>{fmt(f["reached"])}</td>'
        f'<td>{pct(f["share"])}</td></tr>' for f in fn)
    step_rows = ''.join(
        f'<tr><td class="lbl">{k}</td><td>{fmt(v)}</td><td>{safe_pct(v, dr["calls"])}</td></tr>'
        for k, v in dr['by_last_step'])
    kind_rows = ''.join(
        f'<tr><td class="lbl">{k}</td><td>{fmt(v)}</td>'
        f'<td>{"不可（媒体FD）" if k == "フリーダイヤル" else "不可" if k == "非通知" else "可"}</td></tr>'
        for k, v in dr['by_kind'])
    sec_rows = ''.join(f'<tr><td class="lbl">{k}</td><td>{fmt(v)}</td></tr>'
                       for k, v in dr['sec_buckets'])
    return f"""<section>
<h2>離脱の内訳（平常ベース）</h2>
<p class="desc">離脱 = Step "1-7" の登録 webhook が成立しなかった着信。
{fmt(dr['calls'])} 件（受電の {pct(dr['share'])}）。うち発信元が顧客番号（B: {B_SHORT}）で
折り返し架電に使えるのは <b>{fmt(dr['reachable'])} 件</b>。
A: {A_SHORT} の {fmt(dr['by_route']['A'])} 件は発信元が媒体のフリーダイヤルのため架電できない。</p>
<div class="cols2">
<div>
<b style="font-size:12.5px;">シナリオ到達（受電全体・CSVのステップ列順）</b>
<table><tr><th>ステップ</th><th>到達数</th><th>対受電</th></tr>{funnel_rows}</table>
</div>
<div>
<b style="font-size:12.5px;">離脱者の最終到達ステップ</b>
<table><tr><th>最後に到達したステップ</th><th>件数</th><th>構成比</th></tr>{step_rows}</table>
<b style="font-size:12.5px;">発信元番号の種別（折り返し架電の可否）</b>
<table><tr><th>種別</th><th>件数</th><th>架電</th></tr>{kind_rows}</table>
<b style="font-size:12.5px;">通話秒数</b>
<table><tr><th>秒数</th><th>件数</th></tr>{sec_rows}</table>
</div>
</div>
</section>"""


def render_tab_content(D, day_type):
    NDAYS = len(D['daily'])
    EXCL = set(D.get('exclude_dates', []))
    degrade_b = is_degenerate_b(D)
    label = TAB_LABELS[day_type]
    p = D['period']

    kpis = build_kpis(D, degrade_b)
    kpi_html = ''.join(
        f'<div class="kpi"><div class="kv">{v}</div><div class="kl">{k}</div><div class="ks">{s}</div></div>'
        for k, v, s in kpis)

    gw_warn = holiday_warn(D)

    return f'''
<div class="tabmeta">この表示: <b>{label}</b> ／ 日数 {D['day_count']} 日（対象期間 {p['start']}〜{p['end']} のうち該当分。欠測日は分母から除外）</div>

{defs_box(D, degrade_b)}

<div class="kpis">{kpi_html}</div>

<section>
{route_section(D, degrade_b)}
</section>

{anomaly_section(D)}

{test_section_v2(D)}

<section>
<h2>日別推移（暦日ベース・A+B）</h2>
{daily_chart(D['daily'], A_CHART_LABEL, B_CHART_LABEL) if D['daily'] else '<p class="note">このビューに該当する暦日がない。</p>'}
{daily_table(D, NDAYS, head=TAB_HEAD)}
<p class="note">※ ユニーク登録は各日内での重複排除。月計・期間合計行はそれぞれの範囲で重複排除のため日別の単純合計と一致しない。</p>
{gw_warn}
</section>

<section>
<h2>時間帯別（平常ベース合計・稼働順 20時→翌朝）</h2>
<p class="desc">発信元 0120/0800（{A_CHART_LABEL}）とそれ以外（{B_CHART_LABEL}）の受電積み上げ。※異常日は除外済み。</p>
{hourly_chart(D['hourly'], A_CHART_LABEL, B_CHART_LABEL)}
<h3>時間グループ別サマリ</h3>
{group_table(D, head=TAB_HEAD)}
<h3>1時間刻み内訳</h3>
{hourly_table(D, head=TAB_HOURLY_HEAD, note=TAB_HOURLY_NOTE)}
</section>

<section>
<h2>夜間シフト単位（20:00〜翌7:59 を開始日に帰属・全日）</h2>
<p class="desc">暦日集計では1夜のトラフィックが2日に分割されるため、「D日 20時〜D+1日 8時」を1シフトとして再集計した補助ビュー。異常日の昼間スパイクはシフト窓外のため、このビューは異常日の影響をほぼ受けない。</p>
{shift_table(D, EXCL, head=TAB_HEAD)}
</section>

{dropout_section(D)}

{repeat_section(D)}

{quality_section(D)}
'''


CSS_TABS = '''
.tabbar { display: flex; gap: 8px; margin-bottom: 20px; }
.tabbtn { flex: 1; background: #fff; border: 1px solid #d7deea; border-radius: 10px; padding: 12px 14px;
          font-size: 13.5px; font-weight: 600; color: #374151; cursor: pointer; text-align: center; }
.tabbtn .tabsub { display: block; font-weight: 400; font-size: 11px; color: #6b7280; margin-top: 3px; }
.tabbtn.active { background: #111c3d; color: #fff; border-color: #111c3d; }
.tabbtn.active .tabsub { color: #b6c2e2; }
.tabmeta { font-size: 12px; color: #6b7280; margin: -6px 0 18px; }
.footnotes { font-size: 12px; color: #4b5563; background: #f8fafc; border: 1px solid #e5e7eb;
             border-radius: 10px; padding: 12px 16px; margin-top: 6px; }
.footnotes p { margin: 4px 0; }
tr.missing td { background: #f3f4f6; color: #9ca3af; }
tr.missing td.lbl { color: #6b7280; }
'''

TAB_SCRIPT = '''
(function(){
  var tabs = ['all', 'weekday', 'holiday'];
  function selectTab(name, updateHash){
    if (tabs.indexOf(name) === -1) name = 'all';
    tabs.forEach(function(t){
      var panel = document.getElementById('tab-' + t);
      if (panel) panel.style.display = (t === name) ? '' : 'none';
      var btn = document.querySelector('.tabbtn[data-tab="' + t + '"]');
      if (btn) btn.classList.toggle('active', t === name);
    });
    if (updateHash !== false) { history.replaceState(null, '', '#' + name); }
  }
  document.querySelectorAll('.tabbtn').forEach(function(btn){
    btn.addEventListener('click', function(){ selectTab(btn.getAttribute('data-tab')); });
  });
  window.addEventListener('hashchange', function(){
    selectTab(location.hash.replace('#', ''), false);
  });
  var initial = location.hash.replace('#', '');
  selectTab(tabs.indexOf(initial) !== -1 ? initial : 'all', false);
})();
'''


def render(data, sub_label=''):
    """data = {'all': 集計dict, 'weekday': ..., 'holiday': ...} → HTML 文字列"""
    for dt, D in data.items():
        if D.get('day_type') != dt:
            raise ValueError(f'集計の day_type ({D.get("day_type")!r}) がタブ {dt!r} と一致しません')
    D_all = data['all']

    p = D_all['period']
    wd0, wd1 = D_all['daily'][0]['wd'] if D_all['daily'] else '', D_all['daily'][-1]['wd'] if D_all['daily'] else ''
    title_label = sub_label or f'{p["start"]}〜{p["end"]}'

    tabbar = ''.join(
        f'<button class="tabbtn" data-tab="{dt}"><div>{TAB_LABELS[dt]}</div>'
        f'<span class="tabsub">{data[dt]["day_count"]}日</span></button>'
        for dt in ('all', 'weekday', 'holiday'))

    panels = ''.join(
        f'<div id="tab-{dt}" class="tabpanel">{render_tab_content(data[dt], dt)}</div>'
        for dt in ('all', 'weekday', 'holiday'))

    missing_note = format_missing_note(D_all.get('missing_dates', []))
    footnotes = f'<div class="footnotes"><p>※ {DAY_BOUNDARY_NOTE}</p>'
    if missing_note:
        footnotes += f'<p>※ {missing_note}</p>'
    footnotes += '</div>'

    html = f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IVR 電話番号登録分析レポート {title_label}</title>
<style>{CSS}{CSS_TABS}</style></head>
<body><div class="wrap">

<header class="page">
<h1>IVR 受電 × 電話番号登録 分析レポート{f'（{sub_label}）' if sub_label else ''}</h1>
<div class="meta">対象期間: {p['start']}（{wd0}）〜 {p['end']}（{wd1}） ／ タブで「全体」「平日」「休日」を切替（#all / #weekday / #holiday でも直接指定可） ／
データソース: IVRコールログCSV（複数ファイルはIDで重複排除） ／ 作成: {date.today():%Y-%m-%d}</div>
</header>

<div class="tabbar">{tabbar}</div>
{panels}

{footnotes}

<footer>ivr_report.py で生成（依存ライブラリなし・このHTMLは単体で閲覧可能）</footer>
</div>
<script>{TAB_SCRIPT}</script>
</body></html>
'''
    return html


def main():
    if len(sys.argv) < 5:
        raise SystemExit('使い方: render_html_tabs.py all.json weekday.json holiday.json out.html [副題]')
    paths, out_html = sys.argv[1:4], sys.argv[4]
    sub_label = sys.argv[5] if len(sys.argv) > 5 else ''
    data = {dt: json.load(open(f, encoding='utf-8'))
            for dt, f in zip(('all', 'weekday', 'holiday'), paths)}
    html = render(data, sub_label)
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'written: {out_html} ({len(html):,} bytes)')


if __name__ == '__main__':
    main()
