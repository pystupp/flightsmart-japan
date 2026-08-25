"""U.S.–Japan travel-period intelligence.

This is intentionally a travel-demand context layer, not an official public-
holiday authority. Fixed/algorithmic U.S. holidays and commonly busy Japan
travel windows are used to surface planning context without pretending to
forecast prices or delays.
"""
from __future__ import annotations
from datetime import date, timedelta
import calendar


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    shift = (weekday - first.weekday()) % 7
    return first + timedelta(days=shift + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def travel_context(d: date) -> list[dict]:
    y = d.year
    events = []

    def add(start, end, level, ja, en):
        if start <= d <= end:
            events.append({"level": level, "label_ja": ja, "label_en": en, "start": start, "end": end})

    # Japan-focused high-demand travel periods (planning windows, not official-holiday claims).
    add(date(y, 4, 29), date(y, 5, 6), "HIGH", "ゴールデンウィーク旅行期間", "Golden Week travel period")
    add(date(y, 8, 10), date(y, 8, 17), "HIGH", "お盆の旅行混雑期", "Obon travel period")
    add(date(y, 12, 27), date(y, 12, 31), "HIGH", "年末の帰省・旅行混雑期", "Year-end Japan travel period")
    add(date(y, 1, 1), date(y, 1, 5), "HIGH", "年始の帰省・旅行混雑期", "New Year Japan travel period")

    # U.S. travel-demand context.
    thanksgiving = _nth_weekday(y, 11, 3, 4)  # Thursday
    add(thanksgiving - timedelta(days=2), thanksgiving + timedelta(days=3), "HIGH", "米国感謝祭の旅行混雑期", "U.S. Thanksgiving travel period")
    add(date(y, 12, 20), date(y, 12, 26), "HIGH", "クリスマス旅行期間", "Christmas travel period")
    july4 = date(y, 7, 4)
    add(july4 - timedelta(days=2), july4 + timedelta(days=2), "MEDIUM", "米国独立記念日前後", "U.S. Independence Day travel period")
    memorial = _last_weekday(y, 5, 0)
    add(memorial - timedelta(days=2), memorial, "MEDIUM", "メモリアルデー週末", "Memorial Day weekend")
    labor = _nth_weekday(y, 9, 0, 1)
    add(labor - timedelta(days=2), labor, "MEDIUM", "レイバーデー週末", "Labor Day weekend")
    return events


def highest_level(events: list[dict]) -> str:
    levels = {"NONE": 0, "MEDIUM": 1, "HIGH": 2}
    return max((e["level"] for e in events), key=lambda x: levels[x], default="NONE")
