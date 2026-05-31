from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.services.finance_service import category_distribution, current_day_range, dashboard_summary, list_expenses, list_income
from app.utils.dates import current_month_range


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("")
@dashboard_bp.route("/")
@login_required
def home():
    month_start, month_end = current_month_range()
    summary = dashboard_summary(current_user.id, month_start, month_end)
    today_start, today_end = current_day_range()
    today_income = list_income(current_user.id, today_start, today_end)
    today_expenses = list_expenses(current_user.id, today_start, today_end)
    expense_labels, expense_values = category_distribution(list_expenses(current_user.id, month_start, month_end))
    income_labels, income_values = category_distribution(list_income(current_user.id, month_start, month_end))
    return render_template(
        "dashboard.html",
        summary=summary,
        today_income=today_income,
        today_expenses=today_expenses,
        expense_chart={"labels": expense_labels, "values": expense_values, "title": "Expense Distribution"},
        income_chart={"labels": income_labels, "values": income_values, "title": "Income Distribution"},
    )
