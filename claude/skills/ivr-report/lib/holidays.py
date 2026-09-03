#!/usr/bin/env python3
"""日本の国民の祝日を年から算出する（1980〜2099年）。

祝日表をベタ書きすると対象期間を広げるたびに更新が要るため、
法定ルール（固定日・ハッピーマンデー・春分秋分の近似式・振替休日・
国民の休日）から生成する。
"""
from datetime import date, timedelta
from functools import lru_cache

_FIXED = [
    (1, 1, '元日'),
    (2, 11, '建国記念の日'),
    (2, 23, '天皇誕生日'),
    (4, 29, '昭和の日'),
    (5, 3, '憲法記念日'),
    (5, 4, 'みどりの日'),
    (5, 5, 'こどもの日'),
    (8, 11, '山の日'),
    (11, 3, '文化の日'),
    (11, 23, '勤労感謝の日'),
]

# (月, 第n週, 名称) — ハッピーマンデー
_NTH_MONDAY = [
    (1, 2, '成人の日'),
    (7, 3, '海の日'),
    (9, 3, '敬老の日'),
    (10, 2, 'スポーツの日'),
]


def _nth_monday(year, month, nth):
    d = date(year, month, 1)
    d += timedelta(days=(7 - d.weekday()) % 7)  # その月の第1月曜
    return d + timedelta(days=7 * (nth - 1))


def _equinox(year, spring):
    """春分・秋分の日。1980〜2099年で有効な近似式。"""
    base = 20.8431 if spring else 23.2488
    return date(year, 3 if spring else 9,
                int(base + 0.242194 * (year - 1980) - (year - 1980) // 4))


@lru_cache(maxsize=None)
def holidays_of(year):
    """その年の祝日を {date: 名称} で返す（振替休日・国民の休日を含む）。"""
    hs = {date(year, m, d): name for m, d, name in _FIXED}
    for month, nth, name in _NTH_MONDAY:
        hs[_nth_monday(year, month, nth)] = name
    hs[_equinox(year, True)] = '春分の日'
    hs[_equinox(year, False)] = '秋分の日'

    # 振替休日: 日曜と重なった祝日の翌日以降、最初の非祝日
    for d in sorted(hs):
        if d.weekday() != 6:
            continue
        nxt = d + timedelta(days=1)
        while nxt in hs:
            nxt += timedelta(days=1)
        hs[nxt] = '振替休日'

    # 国民の休日: 祝日に挟まれた平日（敬老の日と秋分の日の間など）
    for d in sorted(hs):
        gap = d + timedelta(days=2)
        mid = d + timedelta(days=1)
        if gap in hs and mid not in hs and mid.weekday() != 6:
            hs[mid] = '国民の休日'
    return hs


def is_holiday(d):
    """date または 'YYYY-MM-DD' が祝日かを返す（土日は含まない）。"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d in holidays_of(d.year)


def holiday_name(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return holidays_of(d.year).get(d)


def is_dayoff(d):
    """土日または祝日か（レポートの「休日」判定）。"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d.weekday() >= 5 or is_holiday(d)


def names_in_range(start, end):
    """期間内の祝日を [(YYYY-MM-DD, 名称), ...] で返す。"""
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    out = []
    for y in range(d0.year, d1.year + 1):
        for d, name in sorted(holidays_of(y).items()):
            if d0 <= d <= d1:
                out.append((d.isoformat(), name))
    return out
