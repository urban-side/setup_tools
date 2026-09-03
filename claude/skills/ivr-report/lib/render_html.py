#!/usr/bin/env python3
"""HTML レポートの共有部品（チャート・テーブル・CSS）。

render_html_tabs.py がここから import して再利用する。依存ライブラリなし。
"""
import sys
from datetime import datetime, timedelta

C_A = '#94a3b8'
C_B = '#3b82f6'
C_CALLNZ = '#3b82f6'
C_OK = '#059669'
C_RATE = '#d97706'
C_OFF = '#eef0f3'
C_ANOM = '#dc2626'

def fmt(n):
    return f'{n:,}' if isinstance(n, int) else (f'{n:,.1f}' if isinstance(n, float) else '–')

def pct(v):
    return f'{v:.1f}%' if v is not None else '–'

def grid_step(mx):
    for s in (50, 100, 200, 500, 1000):
        if mx / s <= 8:
            return s
    return 2000

# ---------- SVG: 日別チャート ----------
def daily_chart(days, a_label='A転送', b_label='B直通'):
    n = len(days)
    W, H, TOP, BOT, LPAD = 940, 300, 34, 46, 10
    plot_h = H - TOP - BOT
    normal = [d for d in days if not d['excluded']] or days
    mx = max(int(max(d['calls'] for d in normal) * 1.15), 10)
    clipped = any(d['calls'] > mx for d in days)
    slot = (W - LPAD * 2) / n
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']
    for gv in range(0, mx + 1, grid_step(mx)):
        y = TOP + plot_h - plot_h * gv / mx
        parts.append(f'<line x1="{LPAD}" y1="{y:.0f}" x2="{W-LPAD}" y2="{y:.0f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{LPAD+2}" y="{y-3:.0f}" font-size="10" fill="#9ca3af">{gv}</text>')
    wide = n <= 10
    for i, d in enumerate(days):
        cx = LPAD + slot * i + slot / 2
        bw = 30 if wide else slot * 0.72
        scale = plot_h / mx
        ha = min(d['a_calls'], mx) * scale
        hb = max(0.0, min(d['a_calls'] + d['b_calls'], mx) - min(d['a_calls'], mx)) * scale
        x0 = (cx - bw - bw / 2) if wide else (cx - bw / 2)
        bwd = (bw - 4) if wide else bw
        parts.append(f'<rect x="{x0:.1f}" y="{TOP+plot_h-ha:.1f}" width="{bwd:.1f}" height="{ha:.1f}" fill="{C_A}"/>')
        parts.append(f'<rect x="{x0:.1f}" y="{TOP+plot_h-ha-hb:.1f}" width="{bwd:.1f}" height="{hb:.1f}" fill="{C_B}"/>')
        if d['excluded']:
            parts.append(f'<text x="{cx:.1f}" y="{TOP-4}" font-size="10" font-weight="bold" text-anchor="middle" fill="{C_ANOM}">▲{d["calls"]:,}</text>')
        if wide:
            parts.append(f'<text x="{x0+bwd/2:.1f}" y="{TOP+plot_h-ha-hb-4:.1f}" font-size="10" text-anchor="middle" fill="#4b5563">{d["calls"]}</text>')
            for val, color, dx in ((d['calls_nz'], C_CALLNZ, 0), (d['ok'], C_OK, bw)):
                h = plot_h * min(val, mx) / mx
                parts.append(f'<rect x="{cx+dx-bw/2:.1f}" y="{TOP+plot_h-h:.1f}" width="{bw-4}" height="{h:.1f}" rx="3" fill="{color}"/>')
                parts.append(f'<text x="{cx+dx:.1f}" y="{TOP+plot_h-h-4:.1f}" font-size="10" text-anchor="middle" fill="#4b5563">{val}</text>')
            parts.append(f'<text x="{cx:.1f}" y="{TOP-14}" font-size="12" font-weight="bold" text-anchor="middle" fill="{C_RATE}">{pct(d["rate_all"])}</text>')
        else:
            oh = plot_h * min(d['ok'], mx) / mx
            parts.append(f'<rect x="{cx-bw*0.225:.1f}" y="{TOP+plot_h-oh:.1f}" width="{bw*0.45:.1f}" height="{oh:.1f}" fill="{C_OK}"/>')
        day = d['date'][8:10]
        if wide or day == '01' or (i % 7 == 0) or d['excluded']:
            wd_c = C_ANOM if d['excluded'] else '#dc2626' if d['wd'] == '日' else '#2563eb' if d['wd'] == '土' else '#374151'
            parts.append(f'<text x="{cx:.1f}" y="{H-28}" font-size="{12 if wide else 10}" text-anchor="middle" fill="{wd_c if d["excluded"] else "#374151"}">{d["date"][5:].replace("-","/")}</text>')
            parts.append(f'<text x="{cx:.1f}" y="{H-14}" font-size="{11 if wide else 9}" text-anchor="middle" fill="{wd_c}">({d["wd"]})</text>')
        if not wide and day == '01' and i > 0:
            xb = LPAD + slot * i
            parts.append(f'<line x1="{xb:.1f}" y1="{TOP-6}" x2="{xb:.1f}" y2="{TOP+plot_h}" stroke="#9ca3af" stroke-dasharray="4 3"/>')
    legend = (f'凡例: 左バー=受電（グレー={a_label}/青={b_label}の積み上げ）／ 中=受電(0秒除外) ／ 右緑=登録数 ／ 橙=登録率(全数)' if wide
              else f'凡例: バー=受電（グレー={a_label}/青={b_label}）／ 緑(細)=登録数 ・ 日毎の率は下表参照')
    if clipped:
        legend += ' ／ ▲=異常日(縦軸を平常日レンジに合わせているためバーは頭打ち表示)'
    parts.append(f'<text x="{LPAD}" y="{H-2}" font-size="10" fill="#6b7280">{legend}</text>')
    parts.append('</svg>')
    return ''.join(parts)

# ---------- SVG: 時間帯別チャート ----------
def hourly_chart(hourly, a_label='A(CTI転送)', b_label='B(直通)'):
    W, H, TOP, BOT, LPAD = 940, 320, 40, 40, 10
    plot_h = H - TOP - BOT
    mx = max(h['calls'] for h in hourly)
    slot = (W - LPAD * 2) / len(hourly)
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']
    x_off = LPAD + slot * 12
    parts.append(f'<rect x="{x_off:.1f}" y="{TOP-24}" width="{slot*12:.1f}" height="{plot_h+24}" fill="{C_OFF}"/>')
    parts.append(f'<text x="{x_off+slot*6:.1f}" y="{TOP-10}" font-size="11" text-anchor="middle" fill="#6b7280">IVR稼働時間外(8:00〜19:59)</text>')
    for gv in range(0, mx + 1, grid_step(mx)):
        y = TOP + plot_h - plot_h * gv / mx
        parts.append(f'<line x1="{LPAD}" y1="{y:.0f}" x2="{W-LPAD}" y2="{y:.0f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{LPAD+2}" y="{y-3:.0f}" font-size="10" fill="#9ca3af">{gv}</text>')
    for i, h in enumerate(hourly):
        cx = LPAD + slot * i + slot / 2
        bw = slot * 0.62
        ha = plot_h * h['a_calls'] / mx
        hb = plot_h * h['b_calls'] / mx
        parts.append(f'<rect x="{cx-bw/2:.1f}" y="{TOP+plot_h-ha:.1f}" width="{bw:.1f}" height="{ha:.1f}" fill="{C_A}"/>')
        parts.append(f'<rect x="{cx-bw/2:.1f}" y="{TOP+plot_h-ha-hb:.1f}" width="{bw:.1f}" height="{hb:.1f}" fill="{C_B}"/>')
        oh = plot_h * h['ok'] / mx
        parts.append(f'<rect x="{cx-bw/2:.1f}" y="{TOP+plot_h-oh:.1f}" width="{bw*0.45:.1f}" height="{oh:.1f}" fill="{C_OK}"/>')
        if h['calls']:
            top_y = TOP + plot_h - ha - hb
            parts.append(f'<text x="{cx:.1f}" y="{top_y-14:.1f}" font-size="9" text-anchor="middle" fill="#6b7280">{h["calls"]:,}</text>')
            parts.append(f'<text x="{cx:.1f}" y="{top_y-3:.1f}" font-size="9" font-weight="bold" text-anchor="middle" fill="{C_RATE}">{h["rate_all"]:.0f}%</text>')
        parts.append(f'<text x="{cx:.1f}" y="{H-22}" font-size="10" text-anchor="middle" fill="#374151">{h["hour"]}</text>')
    parts.append(f'<text x="{LPAD}" y="{H-6}" font-size="10" fill="#6b7280">凡例: グレー={a_label} / 青={b_label} の受電積み上げ ／ 緑(細)=登録数 ／ 橙=登録率(全数) ・ 横軸は稼働順 20時→翌19時</text>')
    parts.append('</svg>')
    return ''.join(parts)

# ---------- テーブル ----------
def tel(s):
    return f'{s[:4]}-{s[4:7]}-{s[7:]}' if len(s) >= 10 else s

TABLE_HEAD = '''<tr>
<th></th><th>受電数<br><span>A+B</span></th><th>内A<br><span>CTI転送</span></th><th>内B<br><span>直通</span></th>
<th>受電数<br><span>0秒除外</span></th>
<th>登録数<br><span>1-7 OK</span></th><th>内A</th><th>内B</th>
<th>登録率<br><span>/全着信</span></th><th>登録率<br><span>/0秒除外</span></th>
<th>ﾕﾆｰｸ登録<br><span>入力番号</span></th>
</tr>'''

HOURLY_HEAD = '''<tr>
<th>時間帯</th><th>受電数<br><span>期間合計</span></th><th>内A<br><span>CTI転送</span></th><th>内B<br><span>直通</span></th>
<th>受電数<br><span>日平均</span></th><th>受電数<br><span>0秒除外</span></th>
<th>登録数<br><span>期間合計</span></th><th>内A</th><th>内B</th><th>登録数<br><span>日平均</span></th>
<th>登録率<br><span>/全着信</span></th><th>登録率<br><span>/0秒除外</span></th>
</tr>'''
HOURLY_NOTE = '平常ベース（異常日除外）。受電0件の時間帯は行を省略。グレー行はIVR稼働時間外（ただし着信実績あり）。A経路は8:00に転送が止まりB直通のみ残る。'

def row_cells(d, label, cls=''):
    return f'''<tr{f' class="{cls}"' if cls else ''}>
<td class="lbl">{label}</td>
<td>{fmt(d["calls"])}</td><td class="dim">{fmt(d["a_calls"])}</td><td class="dim">{fmt(d["b_calls"])}</td>
<td>{fmt(d["calls_nz"])}</td>
<td class="ok">{fmt(d["ok"])}</td><td class="dim">{fmt(d["a_ok"])}</td><td class="dim">{fmt(d["b_ok"])}</td>
<td class="rate">{pct(d["rate_all"])}</td><td class="rate">{pct(d["rate_nz"])}</td>
<td class="ok">{fmt(d["uniq_reg"])}</td>
</tr>'''

def daily_table(D, NDAYS, head=TABLE_HEAD):
    rows = []
    for d in D['daily']:
        lbl = f'{d["date"][5:].replace("-","/")} ({d["wd"]})'
        if d['excluded']:
            lbl += '<span class="sub">▲異常日: 平常集計から除外</span>'
        if d.get('missing'):
            lbl += '<span class="sub">◇欠測日: データ0件・日数分母から除外</span>'
        cls = 'anomaly' if d['excluded'] else ('missing' if d.get('missing') else '')
        rows.append(row_cells(d, lbl, cls=cls))
    a = D['daily_avg']
    rows.append(row_cells(dict(calls=a['calls'], a_calls=a['a_calls'], b_calls=a['b_calls'],
                               calls_nz=a['calls_nz'], ok=a['ok'], a_ok=a['a_ok'], b_ok=a['b_ok'],
                               rate_all=a['rate_all'], rate_nz=a['rate_nz'], uniq_reg=a['uniq_reg']),
                          f'日当たり平均<span class="sub">平常{a["n_days"]}日ベース</span>', cls='avg'))
    for m in D.get('monthly', []):
        mn = int(m['month'][5:7])
        rows.append(row_cells(m, f'{mn}月計 ({m["days"]}日)', cls='month'))
        if 'base' in m:
            rows.append(row_cells(m['base'], f'{mn}月計・異常日除く ({m["base_days"]}日)', cls='month'))
    rows.append(row_cells(D['total'], f'期間合計・平常ベース<span class="sub">異常日除く {a["n_days"]}日</span>', cls='total'))
    rows.append(row_cells(D['total_incl'], f'期間合計・異常日込み<span class="sub">{NDAYS}日</span>', cls='total'))
    return f'<table>{head}{"".join(rows)}</table>'

def shift_table(D, EXCL, head=TABLE_HEAD):
    rows = [row_cells(s, f'{s["date"][5:].replace("-","/")} ({s["wd"]}) 20時〜翌8時'
                      + ('<span class="sub">◇欠測日</span>' if s.get('missing') else ''),
                      cls='anomaly' if s['date'] in EXCL else ('missing' if s.get('missing') else ''))
            for s in D['shifts']]
    a = D['shift_avg']
    avg = f'''<tr class="avg">
<td class="lbl">シフト当たり平均</td>
<td>{fmt(a["calls"])}</td><td>–</td><td>–</td><td>–</td>
<td class="ok">{fmt(a["ok"])}</td><td>–</td><td>–</td>
<td class="rate">{pct(a["rate_all"])}</td><td>–</td>
<td class="ok">{fmt(a["uniq_reg"])}</td>
</tr>'''
    return f'<table>{head}{"".join(rows)}{avg}</table>'

def hourly_table(D, head=HOURLY_HEAD, note=HOURLY_NOTE):
    rows = []
    for h in D['hourly']:
        if h['calls'] == 0:
            continue
        cls = '' if (h['hour'] >= 20 or h['hour'] < 8) else 'offband'
        rows.append(f'''<tr{f' class="{cls}"' if cls else ''}>
<td class="lbl">{h["hour"]}:00〜{h["hour"]}:59</td>
<td>{fmt(h["calls"])}</td><td class="dim">{fmt(h["a_calls"])}</td><td class="dim">{fmt(h["b_calls"])}</td>
<td>{fmt(h["avg_calls"])}</td><td>{fmt(h["calls_nz"])}</td>
<td class="ok">{fmt(h["ok"])}</td><td class="dim">{fmt(h["a_ok"])}</td><td class="dim">{fmt(h["b_ok"])}</td>
<td class="ok">{fmt(h["avg_ok"])}</td>
<td class="rate">{pct(h["rate_all"])}</td><td class="rate">{pct(h["rate_nz"])}</td>
</tr>''')
    return f'<table>{head}{"".join(rows)}</table><p class="note">{note}</p>'

def group_table(D, head=TABLE_HEAD):
    rows = [row_cells(g, f'{g["name"]}<span class="sub">{g["note"]}</span>') for g in D['groups']]
    return f'<table>{head}{"".join(rows)}</table>'

def route_compare_table(D):
    A, B = D['routes']['A'], D['routes']['B']
    t = D['total']
    return f'''<table class="routecmp">
<tr><th></th><th>A: CTI転送<br><span>お客さん→CTI→IVR</span></th><th>B: IVR直通<br><span>お客さん→IVR</span></th></tr>
<tr><td class="lbl">発信元番号の意味</td><td>転送元の 0120 回線（{A["src_count"]}本）<br><b>人物特定不可</b></td><td>ほぼ本人の番号</td></tr>
<tr><td class="lbl">受電数</td><td>{fmt(A["calls"])} 件（{100*A["calls"]/t["calls"]:.0f}%）</td><td>{fmt(B["calls"])} 件（{100*B["calls"]/t["calls"]:.0f}%）</td></tr>
<tr><td class="lbl">0秒切断</td><td>{fmt(A["zero"])} 件（{100*A["zero"]/A["calls"]:.0f}%）転送リトライ由来か</td><td>{fmt(B["zero"])} 件（{100*B["zero"]/B["calls"]:.0f}%）</td></tr>
<tr><td class="lbl">登録数（1-7 OK）</td><td class="ok">{fmt(A["ok"])} 件</td><td class="ok">{fmt(B["ok"])} 件</td></tr>
<tr><td class="lbl">登録率（全数 / 0秒除外）</td><td class="rate">{pct(A["rate_all"])} / {pct(A["rate_nz"])}</td><td class="rate">{pct(B["rate_all"])} / {pct(B["rate_nz"])}</td></tr>
<tr><td class="lbl">ユニーク登録人数（入力番号）</td><td class="ok">{fmt(A["uniq_reg"])} 人</td><td class="ok">{fmt(B["uniq_reg"])} 人</td></tr>
<tr><td class="lbl">人物ファネル</td><td>算出不能（分母の人数が不明）</td><td class="hl"><b>受電 {fmt(t["b_persons"])} 人 → 登録 {fmt(t["b_persons_ok"])} 人 = {pct(t["rate_b_person"])}</b></td></tr>
</table>'''

def b_funnel_table(D):
    rows = []
    for d in D['daily']:
        lbl = f'{d["date"][5:].replace("-","/")} ({d["wd"]})'
        if d['excluded']:
            lbl += '<span class="sub">▲異常日</span>'
        rows.append(f'''<tr{' class="anomaly"' if d['excluded'] else ''}>
<td class="lbl">{lbl}</td>
<td>{fmt(d["b_persons"])}</td><td class="ok">{fmt(d["b_persons_ok"])}</td>
<td class="rate">{pct(d["rate_b_person"])}</td>
<td class="ok">{fmt(d["a_uniq_reg"])}</td><td class="ok">{fmt(d["uniq_reg"])}</td>
</tr>''')
    a, t, ti = D['daily_avg'], D['total'], D['total_incl']
    rows.append(f'''<tr class="avg">
<td class="lbl">日当たり平均<span class="sub">平常{a["n_days"]}日ベース</span></td>
<td>{fmt(a["b_persons"])}</td><td class="ok">{fmt(a["b_persons_ok"])}</td>
<td class="rate">{pct(a["rate_b_person"])}</td>
<td>–</td><td class="ok">{fmt(a["uniq_reg"])}</td>
</tr>''')
    for m in D.get('monthly', []):
        mn = int(m['month'][5:7])
        src = m.get('base', m)
        sfx = '・異常日除く' if 'base' in m else ''
        rows.append(f'''<tr class="month">
<td class="lbl">{mn}月計{sfx}</td>
<td>{fmt(src["b_persons"])}</td><td class="ok">{fmt(src["b_persons_ok"])}</td>
<td class="rate">{pct(src["rate_b_person"])}</td>
<td class="ok">{fmt(src["a_uniq_reg"])}</td><td class="ok">{fmt(src["uniq_reg"])}</td>
</tr>''')
    rows.append(f'''<tr class="total">
<td class="lbl">期間合計・平常ベース<span class="sub">期間内で重複排除</span></td>
<td>{fmt(t["b_persons"])}</td><td class="ok">{fmt(t["b_persons_ok"])}</td>
<td class="rate">{pct(t["rate_b_person"])}</td>
<td class="ok">{fmt(t["a_uniq_reg"])}</td><td class="ok">{fmt(t["uniq_reg"])}</td>
</tr>''')
    rows.append(f'''<tr class="total">
<td class="lbl">期間合計・異常日込み</td>
<td>{fmt(ti["b_persons"])}</td><td class="ok">{fmt(ti["b_persons_ok"])}</td>
<td class="rate">{pct(ti["rate_b_person"])}</td>
<td class="ok">{fmt(ti["a_uniq_reg"])}</td><td class="ok">{fmt(ti["uniq_reg"])}</td>
</tr>''')
    head = '''<tr>
<th>日付</th><th>B: 受電人数<br><span>発信元ﾕﾆｰｸ</span></th><th>B: 登録人数</th><th>B: 人物登録率</th>
<th>A: 登録人数<br><span>入力番号ﾕﾆｰｸ</span></th><th>全体ﾕﾆｰｸ登録<br><span>A+B重複排除</span></th>
</tr>'''
    note = '<p class="note">※ 月計・期間合計のユニークはそれぞれの範囲内で重複排除しているため、日別の単純合計とは一致しない。</p>'
    return f'<table>{head}{"".join(rows)}</table>{note}'

def anomaly_section(D):
    if not D['anomalies']:
        return ''
    parts = []
    for an in D['anomalies']:
        hh_rows = ''.join(
            f'<tr><td class="lbl">{h["hour"]}時台</td><td>{fmt(h["calls"])}</td><td class="ok">{fmt(h["ok"])}</td></tr>'
            for h in an['hourly'])
        srcs = ''.join(f'<li>{s[0][:4]}-{s[0][4:7]}-{s[0][7:]}: {s[1]}件</li>' for s in an['top_srcs'])
        parts.append(f'''
<h3>{an["date"]}（{an["wd"]}）: 受電 {fmt(an["b_calls"])} 件（平常日平均の約{an["b_calls"]/max(1,D["daily_avg"]["calls"]):.0f}倍）</h3>
<div class="cols2">
<div>
<ul class="plain">
<li>着信の {100*an["daytime"]/an["b_calls"]:.0f}%（{fmt(an["daytime"])}件）が<b>通常は着信ゼロの昼間帯（9〜18時台）</b>に発生。CTIが終日IVRへ転送されていた・もしくは案内経路が変わった日とみられる。</li>
<li>経路構成: A {fmt(an["b_a_calls"])} ／ B {fmt(an["b_b_calls"])}。転送元は平常時と同じクライアント0120回線群（右上位）。</li>
<li>0秒率 {100*(an["b_calls"]-an["b_calls_nz"])/an["b_calls"]:.0f}%・通話中央値 {an["med_sec"]}秒・<b>登録 {fmt(an["b_ok"])} 件（ユニーク {fmt(an["b_uniq_reg"])} 番号）</b>と、実顧客トラフィックの挙動。</li>
<li>B人物ファネル（この日単独）: {fmt(an["b_b_persons"])} 人 → {fmt(an["b_b_persons_ok"])} 人 = {pct(an["b_rate_b_person"])}。</li>
<li>本レポートの「平常ベース」指標はこの日を除外して算出。異常日込みの値は各表の「込み」行を参照。</li>
</ul>
<b style="font-size:12.5px;">転送元上位</b>
<ul class="plain">{srcs}</ul>
</div>
<div>
<b style="font-size:12.5px;">時間帯分布（この日）</b>
<table><tr><th>時間帯</th><th>受電</th><th>登録</th></tr>{hh_rows}</table>
</div>
</div>''')
    return f'''<section>
<h2>異常日の内訳（平常ベースから除外した日）</h2>
{''.join(parts)}
</section>'''


CSS = '''
* { box-sizing: border-box; margin: 0; }
body { font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", Meiryo, sans-serif;
       background: #f3f4f6; color: #1f2937; line-height: 1.6; }
.wrap { max-width: 1000px; margin: 0 auto; padding: 28px 20px 60px; }
header.page { background: #111c3d; color: #fff; border-radius: 14px; padding: 26px 30px; margin-bottom: 22px; }
header.page h1 { font-size: 21px; margin-bottom: 6px; }
header.page .meta { font-size: 12.5px; color: #b6c2e2; }
.defs { background: #eef4ff; border: 1px solid #c7d9f7; border-radius: 10px; padding: 14px 18px;
        font-size: 12.5px; margin-bottom: 26px; }
.defs b { color: #1d4ed8; }
.defs li { margin-left: 18px; }
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 30px; }
.kpi { background: #fff; border-radius: 12px; padding: 16px 18px 13px; box-shadow: 0 1px 3px rgba(0,0,0,.07); }
.kpi .kv { font-size: 26px; font-weight: 700; color: #111c3d; }
.kpi .kl { font-size: 13px; font-weight: 600; color: #374151; margin-top: 2px; }
.kpi .ks { font-size: 11px; color: #6b7280; margin-top: 3px; }
section { background: #fff; border-radius: 12px; padding: 22px 24px; margin-bottom: 24px;
          box-shadow: 0 1px 3px rgba(0,0,0,.07); }
section h2 { font-size: 16px; border-left: 4px solid #2563eb; padding-left: 10px; margin-bottom: 6px; }
section h3 { font-size: 14px; margin-top: 18px; margin-bottom: 4px; }
section .desc { font-size: 12.5px; color: #6b7280; margin-bottom: 14px; }
svg { width: 100%; height: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
th { background: #f1f5fb; padding: 7px 5px; border-bottom: 2px solid #d7deea; font-size: 11.5px; }
th span { font-weight: 400; font-size: 10px; color: #6b7280; }
td { padding: 6px 5px; border-bottom: 1px solid #eceff3; text-align: right; font-variant-numeric: tabular-nums; }
td.lbl { text-align: left; font-weight: 600; white-space: nowrap; }
td .sub { display: block; font-weight: 400; font-size: 10px; color: #9ca3af; }
td.ok { color: #047857; font-weight: 600; }
td.rate { color: #b45309; font-weight: 600; }
td.dim { color: #6b7280; }
td.hl { background: #ecfdf5; }
tr.avg td { background: #fffbeb; border-top: 2px solid #f0d48a; font-weight: 700; }
tr.month td { background: #f5f3ff; font-weight: 700; }
tr.total td { background: #eef4ff; font-weight: 700; }
tr.offband td { background: #f6f7f8; }
tr.anomaly td { background: #fef2f2; }
table.routecmp td { text-align: left; vertical-align: top; }
.note { font-size: 11.5px; color: #6b7280; margin-top: 8px; }
.warn { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 10px 14px;
        font-size: 12.5px; margin-top: 12px; }
.info { background: #eef4ff; border: 1px solid #c7d9f7; border-radius: 8px; padding: 10px 14px;
        font-size: 12.5px; margin-top: 12px; }
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
ul.plain { font-size: 12.5px; padding-left: 20px; }
footer { font-size: 11px; color: #9ca3af; text-align: center; margin-top: 10px; }
'''
