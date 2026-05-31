from __future__ import annotations

from datetime import date, datetime, timedelta
from collections import defaultdict

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.forms import ReportFilterForm
from app.services.finance_service import (
    category_distribution,
    day_series,
    week_series,
    month_series,
    get_earliest_transaction_date,
    list_expenses,
    list_income,
)
from app.services.report_service import build_pdf_report, report_summary
from app.utils.dates import (
    available_months,
    available_weeks,
    available_years,
    current_month_range,
    date_range_for_specific,
)


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

_FALLBACK_EARLIEST = date(date.today().year, 1, 1)


def _get_earliest(user_id: str) -> date:
    earliest = get_earliest_transaction_date(user_id)
    return earliest if earliest else _FALLBACK_EARLIEST


def _build_pie_payload(items):
    """Category-level pie/doughnut data."""
    labels, values = category_distribution(items)
    return {"labels": labels, "values": values}


def _as_date(value) -> date:
    return value.date() if isinstance(value, datetime) else value


def _week_start(value: date) -> date:
    return value - timedelta(days=(value.weekday() + 1) % 7)


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _transaction_totals_by_day(items) -> dict[date, float]:
    totals: dict[date, float] = defaultdict(float)
    for item in items:
        item_date = item.get("date")
        if not item_date:
            continue
        totals[_as_date(item_date)] += float(item.get("amount", 0) or 0)
    return totals


def _build_daily_series(items, start_date: date, end_date: date) -> dict:
    totals = _transaction_totals_by_day(items)
    labels: list[str] = []
    values: list[float] = []
    current = start_date
    while current <= end_date:
        labels.append(current.strftime("%d %b"))
        values.append(round(totals.get(current, 0.0), 2))
        current += timedelta(days=1)
    return {"labels": labels, "values": values}


def _build_weekly_series(items, start_date: date, end_date: date) -> dict:
    totals: dict[date, float] = defaultdict(float)
    for item in items:
        item_date = item.get("date")
        if not item_date:
            continue
        day = _as_date(item_date)
        totals[_week_start(day)] += float(item.get("amount", 0) or 0)

    labels: list[str] = []
    values: list[float] = []
    current = _week_start(start_date)
    end_week = _week_start(end_date)
    while current <= end_week:
        labels.append(f"{current.strftime('%d %b')} – {(current + timedelta(days=6)).strftime('%d %b %Y')}")
        values.append(round(totals.get(current, 0.0), 2))
        current += timedelta(weeks=1)
    return {"labels": labels, "values": values}


def _build_monthly_series(items, start_date: date, end_date: date) -> dict:
    totals: dict[tuple[int, int], float] = defaultdict(float)
    for item in items:
        item_date = item.get("date")
        if not item_date:
            continue
        day = _as_date(item_date)
        totals[(day.year, day.month)] += float(item.get("amount", 0) or 0)

    labels: list[str] = []
    values: list[float] = []
    current = _month_start(start_date)
    end_month = _month_start(end_date)
    while current <= end_month:
        labels.append(current.strftime("%b %Y"))
        values.append(round(totals.get((current.year, current.month), 0.0), 2))
        current = _next_month(current)
    return {"labels": labels, "values": values}


def _build_period_charts(income_items, expense_items, period: str, start_date: date, end_date: date) -> dict:
    """Build period-appropriate bar chart data.

    Week  → day-wise only
    Month → day-wise + week-wise
    Year  → month-wise only
    """
    charts = {}

    if period == "week":
        inc_day = _build_daily_series(income_items, start_date, end_date)
        exp_day = _build_daily_series(expense_items, start_date, end_date)
        charts["day"] = {
            "income": inc_day,
            "expense": exp_day,
            "title": "Day-wise",
        }

    elif period == "month":
        inc_day = _build_daily_series(income_items, start_date, end_date)
        exp_day = _build_daily_series(expense_items, start_date, end_date)
        charts["day"] = {
            "income": inc_day,
            "expense": exp_day,
            "title": "Day-wise",
        }
        inc_week = _build_weekly_series(income_items, start_date, end_date)
        exp_week = _build_weekly_series(expense_items, start_date, end_date)
        charts["week"] = {
            "income": inc_week,
            "expense": exp_week,
            "title": "Week-wise",
        }

    else:  # year
        inc_month = _build_monthly_series(income_items, start_date, end_date)
        exp_month = _build_monthly_series(expense_items, start_date, end_date)
        charts["month"] = {
            "income": inc_month,
            "expense": exp_month,
            "title": "Month-wise",
        }

    return charts


def _resolve_date_range(period: str, range_value: str | None):
    """Return (start_date, end_date) for the selected period + range_value."""
    if range_value:
        return date_range_for_specific(period, range_value)
    earliest = _get_earliest(current_user.id)
    if period == "week":
        options = available_weeks(earliest)
    elif period == "year":
        options = available_years(earliest)
    else:
        options = available_months(earliest)
    first = options[0] if options else None
    if first:
        return date_range_for_specific(period, first["value"])
    return current_month_range()


@reports_bp.route("/ranges")
@login_required
def ranges():
    """JSON API: return available ranges for a given period type."""
    period = request.args.get("period", "month")
    earliest = _get_earliest(current_user.id)
    if period == "week":
        items = available_weeks(earliest)
    elif period == "year":
        items = available_years(earliest)
    else:
        items = available_months(earliest)
    return jsonify(items)


@reports_bp.route("")
@login_required
def index():
    form = ReportFilterForm(request.args)
    period = request.args.get("period", "month")
    range_value = request.args.get("range_value") or None
    start_date, end_date = _resolve_date_range(period, range_value)
    start_day = start_date.date()
    end_day = end_date.date()
    expenses = list_expenses(current_user.id, start_date, end_date)
    income_items = list_income(current_user.id, start_date, end_date)
    summary = report_summary(current_user.id, start_date, end_date)

    # Pie charts (category distribution)
    income_pie = _build_pie_payload(income_items)
    expense_pie = _build_pie_payload(expenses)

    # Period-specific bar charts
    period_charts = _build_period_charts(income_items, expenses, period, start_day, end_day)

    # Available ranges for the dropdown
    earliest = _get_earliest(current_user.id)
    if period == "week":
        range_options = available_weeks(earliest)
    elif period == "year":
        range_options = available_years(earliest)
    else:
        range_options = available_months(earliest)

    return render_template(
        "reports/index.html",
        form=form,
        period=period,
        range_value=range_value or (range_options[0]["value"] if range_options else ""),
        range_options=range_options,
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        income_pie=income_pie,
        expense_pie=expense_pie,
        period_charts=period_charts,
    )


@reports_bp.route("/pdf")
@login_required
def pdf():
    period = request.args.get("period", "month")
    range_value = request.args.get("range_value") or None
    start_date, end_date = _resolve_date_range(period, range_value)
    pdf_buffer = build_pdf_report(
        {"name": current_user.name, "email": current_user.email},
        period,
        period.title(),
        start_date,
        end_date,
        current_user.id,
    )
    safe_range = range_value or "latest"
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"fintrack-inr-report-{period}-{safe_range}-{stamp}.pdf"
    response = send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
