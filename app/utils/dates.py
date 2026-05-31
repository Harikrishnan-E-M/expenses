from __future__ import annotations

from datetime import date, datetime, timedelta
from calendar import month_abbr


def today_range() -> tuple[datetime, datetime]:
    start = datetime.combine(date.today(), datetime.min.time())
    end = datetime.combine(date.today(), datetime.max.time())
    return start, end


def _week_sunday_start(d: date) -> date:
    """Return the Sunday that starts the ISO week containing *d*.
    Week: Sunday – Saturday.
    """
    # weekday(): Mon=0 … Sun=6  →  days_since_sunday = (weekday + 1) % 7
    return d - timedelta(days=(d.weekday() + 1) % 7)


def current_week_range() -> tuple[datetime, datetime]:
    today = date.today()
    sunday = _week_sunday_start(today)
    start = datetime.combine(sunday, datetime.min.time())
    end = datetime.combine(sunday + timedelta(days=6), datetime.max.time())
    return start, end


def current_month_range() -> tuple[datetime, datetime]:
    today = date.today()
    start = datetime(today.year, today.month, 1)
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    end = datetime.combine(next_month - timedelta(days=1), datetime.max.time())
    return start, end


def current_year_range() -> tuple[datetime, datetime]:
    start = datetime(date.today().year, 1, 1)
    end = datetime.combine(date(date.today().year, 12, 31), datetime.max.time())
    return start, end


def financial_year_range(year: int | None = None) -> tuple[datetime, datetime]:
    today = date.today()
    if year is None:
        year = today.year if today.month >= 4 else today.year - 1
    start = datetime(year, 4, 1)
    end = datetime.combine(date(year + 1, 3, 31), datetime.max.time())
    return start, end


def date_range_for_period(period: str, year: int | None = None) -> tuple[datetime, datetime]:
    if period == "week":
        return current_week_range()
    if period == "month":
        return current_month_range()
    if period == "year":
        return current_year_range()
    return financial_year_range(year)


# ---------------------------------------------------------------------------
# Dynamic range enumeration helpers
# ---------------------------------------------------------------------------

def available_weeks(earliest: date) -> list[dict]:
    """Return all Sunday-to-Saturday weeks from the week containing *earliest*
    up to the current week, newest first.

    Each entry: {"value": "YYYY-MM-DD", "label": "DD Mon – DD Mon YYYY"}
    The value is the ISO date of the week's Sunday.
    """
    today = date.today()
    # Anchor both to the Sunday of their respective weeks
    start_sunday = _week_sunday_start(earliest)
    current_sunday = _week_sunday_start(today)

    weeks = []
    sunday = current_sunday
    while sunday >= start_sunday:
        saturday = sunday + timedelta(days=6)
        label = f"{sunday.strftime('%d %b')} – {saturday.strftime('%d %b %Y')}"
        weeks.append({"value": sunday.isoformat(), "label": label})
        sunday -= timedelta(weeks=1)
    return weeks


def available_months(earliest: date) -> list[dict]:
    """Return all months from *earliest* up to the current month, newest first.

    Each entry: {"value": "YYYY-MM", "label": "Mon YYYY"}
    """
    today = date.today()
    months = []
    yr, mo = today.year, today.month
    while (yr, mo) >= (earliest.year, earliest.month):
        label = f"{month_abbr[mo]} {yr}"
        months.append({"value": f"{yr}-{mo:02d}", "label": label})
        mo -= 1
        if mo == 0:
            mo = 12
            yr -= 1
    return months


def available_years(earliest: date) -> list[dict]:
    """Return all calendar years from *earliest* up to the current year, newest first.

    Each entry: {"value": "YYYY", "label": "YYYY"}
    """
    today = date.today()
    years = []
    for yr in range(today.year, earliest.year - 1, -1):
        years.append({"value": str(yr), "label": str(yr)})
    return years


def date_range_for_specific(period_type: str, range_value: str) -> tuple[datetime, datetime]:
    """Resolve a period type + range value into (start_datetime, end_datetime).

    period_type: 'week' | 'month' | 'year'
    range_value:
      - week  → ISO date string of the week's Sunday ('YYYY-MM-DD')
      - month → 'YYYY-MM'
      - year  → 'YYYY'
    """
    if period_type == "week":
        sunday = date.fromisoformat(range_value)
        start = datetime.combine(sunday, datetime.min.time())
        end = datetime.combine(sunday + timedelta(days=6), datetime.max.time())
        return start, end

    if period_type == "month":
        yr, mo = map(int, range_value.split("-"))
        start = datetime(yr, mo, 1)
        if mo == 12:
            next_month = date(yr + 1, 1, 1)
        else:
            next_month = date(yr, mo + 1, 1)
        end = datetime.combine(next_month - timedelta(days=1), datetime.max.time())
        return start, end

    if period_type == "year":
        yr = int(range_value)
        start = datetime(yr, 1, 1)
        end = datetime.combine(date(yr, 12, 31), datetime.max.time())
        return start, end

    # Fallback – current month
    return current_month_range()
