#!/usr/bin/env python3
"""IVR コールログ CSV から分析レポートを生成する。

  python3 ivr_report.py ログ.csv

期間を指定しなければログに含まれる全期間が対象になる。出力は既定で
HTML（タブ切替・単体で閲覧可能）／Markdown／離脱者CSV の 3 種で、
実行のたびに output/<実行日時>/ を切ってその中に書き出す。

  python3 ivr_report.py 5月.csv 6月.csv --format html --title "拠点A（TENANT_A）"
  python3 ivr_report.py ログ.csv --start 2026-06-01 --end 2026-06-30 --exclude-dates 2026-06-03

Python 3.9 以上。依存ライブラリなし。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))

from analyze import LogFormatError, aggregate, dropouts, load_calls  # noqa: E402
import render_csv  # noqa: E402
import render_html_tabs  # noqa: E402
import render_markdown  # noqa: E402

FORMATS = ('html', 'md', 'csv', 'json')
DAY_TYPES = ('all', 'weekday', 'holiday')


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description='IVR コールログ CSV から分析レポートを生成する',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='例:\n'
               '  python3 ivr_report.py input_logs/report_202606.csv\n'
               '  python3 ivr_report.py input_logs/*.csv --title "拠点A（TENANT_A）" --format html,csv\n')
    ap.add_argument('csvs', nargs='+', metavar='ログCSV',
                    help='IVR 事業者の IVR コールログ CSV（複数可。ID で重複排除する）')
    ap.add_argument('-o', '--out', default='output', metavar='DIR',
                    help='出力先ディレクトリ（既定: output）。'
                         'この下に実行日時のフォルダを作り、その中に書き出す')
    ap.add_argument('-f', '--format', default='html,md,csv', metavar='FMT',
                    help=f'出力形式をカンマ区切りで指定 {FORMATS}（既定: html,md,csv）')
    ap.add_argument('-t', '--title', default='', metavar='副題',
                    help='レポート見出しの副題（例: "拠点A（TENANT_A）"）')
    ap.add_argument('--start', metavar='YYYY-MM-DD', help='集計開始日（既定: ログの最初の日）')
    ap.add_argument('--end', metavar='YYYY-MM-DD', help='集計終了日（既定: ログの最後の日）')
    ap.add_argument('--exclude-dates', nargs='*', default=[], metavar='YYYY-MM-DD',
                    help='異常日。「平常ベース」から除外し、内訳を別掲する')
    ap.add_argument('--missing-dates', nargs='*', default=[], metavar='YYYY-MM-DD',
                    help='データ欠測日。日平均などの日数分母から除外する')
    ap.add_argument('--test-sources', nargs='*', default=[], metavar='番号',
                    help='テスト・ボットの発信元番号。主集計から分離して別掲する')
    ap.add_argument('--md-days', type=int, default=0, metavar='N',
                    help='Markdown の日別表を直近 N 日に絞る（既定: 0＝全日）')
    ap.add_argument('--prefix', default='ivr_report', metavar='NAME',
                    help='出力ファイル名の接頭辞（既定: ivr_report）')
    return ap.parse_args(argv)


def build(args):
    calls, meta = load_calls(args.csvs)
    start = args.start or meta['first']
    end = args.end or meta['last']
    if start > end:
        raise SystemExit(f'--start ({start}) が --end ({end}) より後になっています')

    data = {dt: aggregate(calls, meta, start, end, dt,
                          args.exclude_dates, args.test_sources, args.missing_dates)
            for dt in DAY_TYPES}
    if data['all']['total']['calls'] == 0:
        raise SystemExit(
            f'{start}〜{end} に集計対象の着信がありません'
            f'（ログの範囲は {meta["first"]}〜{meta["last"]}）')
    return calls, meta, data, start, end


def main(argv=None):
    args = parse_args(argv)
    fmts = [f.strip() for f in args.format.split(',') if f.strip()]
    unknown = [f for f in fmts if f not in FORMATS]
    if unknown:
        raise SystemExit(f'未知の出力形式: {unknown}（指定できるのは {FORMATS}）')

    for p in args.csvs:
        if not Path(p).is_file():
            raise SystemExit(f'ファイルが見つかりません: {p}')

    try:
        calls, meta, data, start, end = build(args)
    except LogFormatError as e:
        raise SystemExit(f'ログの形式を解釈できません。\n{e}')

    # 実行のたびに日時フォルダを切る。前回の結果を上書きせず、並べて比較できる。
    run = datetime.now().strftime('%Y%m%d-%H%M%S')
    out = Path(args.out) / run
    n = 2
    while out.exists():  # 同一秒に何度も走らせた場合
        out = Path(args.out) / f'{run}_{n}'
        n += 1
    out.mkdir(parents=True)
    stem = f'{args.prefix}_{start.replace("-", "")}-{end.replace("-", "")}'
    t = data['all']['total']
    d = data['all']['dropout']
    print(f'対象期間 {start}〜{end} ／ 受電 {t["calls"]:,} 件 ／ '
          f'登録 {t["ok"]:,} 件（{t["rate_all"]}%）／ 離脱 {d["calls"]:,} 件')
    if meta['dup_removed']:
        print(f'  ID重複 {meta["dup_removed"]:,} 行を排除しました')

    written = []
    if 'html' in fmts:
        path = out / f'{stem}.html'
        path.write_text(render_html_tabs.render(data, args.title), encoding='utf-8')
        written.append(path)
    if 'md' in fmts:
        path = out / f'{stem}.md'
        path.write_text(render_markdown.render(data, args.title, args.md_days), encoding='utf-8')
        written.append(path)
    if 'csv' in fmts:
        path = out / f'{stem}_dropouts.csv'
        n = render_csv.write(dropouts(calls, start, end, args.test_sources), path)
        written.append(path)
        note = ('（レポートの離脱数は異常日を除いた平常ベースのため '
                f'{d["calls"]:,} 件）' if n != d['calls'] else '')
        print(f'  離脱者 {n:,} 件を CSV に書き出しました{note}')
    if 'json' in fmts:
        for dt in DAY_TYPES:
            path = out / f'{stem}_{dt}.json'
            path.write_text(json.dumps(data[dt], ensure_ascii=False, indent=1), encoding='utf-8')
            written.append(path)

    print(f'出力: {out}/')
    for p in written:
        print(f'  {p.name}  ({p.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
