from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.finance_service import list_expenses, list_income, list_wallets


_PALETTE = [
    colors.HexColor("#0f766e"),
    colors.HexColor("#2563eb"),
    colors.HexColor("#f59e0b"),
    colors.HexColor("#ef4444"),
    colors.HexColor("#8b5cf6"),
    colors.HexColor("#14b8a6"),
    colors.HexColor("#f97316"),
    colors.HexColor("#22c55e"),
]


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


def _frame_from_items(items):
    frame = pd.DataFrame(items)
    if frame.empty or "date" not in frame.columns or "amount" not in frame.columns:
        return frame.iloc[0:0]
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"])
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce").fillna(0.0)
    return frame


def _series_by_day(frame: pd.DataFrame, start_date: date, end_date: date) -> tuple[list[str], list[float]]:
    totals = defaultdict(float)
    if not frame.empty:
        grouped = frame.groupby(frame["date"].dt.date)["amount"].sum()
        totals.update({key: float(value) for key, value in grouped.items()})
    labels: list[str] = []
    values: list[float] = []
    current = start_date
    while current <= end_date:
        labels.append(current.strftime("%d %b"))
        values.append(round(totals.get(current, 0.0), 2))
        current += timedelta(days=1)
    return labels, values


def _series_by_week(frame: pd.DataFrame, start_date: date, end_date: date) -> tuple[list[str], list[float]]:
    totals = defaultdict(float)
    if not frame.empty:
        week_starts = frame["date"].dt.date.map(_week_start)
        grouped = frame.groupby(week_starts)["amount"].sum()
        totals.update({key: float(value) for key, value in grouped.items()})
    labels: list[str] = []
    values: list[float] = []
    current = _week_start(start_date)
    end_week = _week_start(end_date)
    while current <= end_week:
        labels.append(f"{current.strftime('%d %b')} – {(current + timedelta(days=6)).strftime('%d %b %Y')}")
        values.append(round(totals.get(current, 0.0), 2))
        current += timedelta(weeks=1)
    return labels, values


def _series_by_month(frame: pd.DataFrame, start_date: date, end_date: date) -> tuple[list[str], list[float]]:
    totals = defaultdict(float)
    if not frame.empty:
        month_keys = frame["date"].dt.to_period("M")
        grouped = frame.groupby(month_keys)["amount"].sum()
        totals.update({key: float(value) for key, value in grouped.items()})
    labels: list[str] = []
    values: list[float] = []
    current = _month_start(start_date)
    end_month = _month_start(end_date)
    while current <= end_month:
        key = current.strftime("%Y-%m")
        labels.append(current.strftime("%b %Y"))
        values.append(round(totals.get(pd.Period(key, freq="M"), 0.0), 2))
        current = _next_month(current)
    return labels, values


def _build_pie_drawing(title: str, labels: list[str], values: list[float], width: float = 245, height: float = 165):
    drawing = Drawing(width, height)
    drawing.add(String(width / 2, height - 12, title, fontName="Helvetica-Bold", fontSize=10, textAnchor="middle"))
    if not labels or not values or not any(value > 0 for value in values):
        drawing.add(String(width / 2, height / 2, "No data for this period.", fontName="Helvetica", fontSize=9, textAnchor="middle", fillColor=colors.HexColor("#6b7280")))
        return drawing

    pie = Pie()
    pie.x = 30
    pie.y = 8
    pie.width = width - 60
    pie.height = height - 36
    pie.data = values
    pie.labels = labels
    pie.sideLabels = True
    pie.simpleLabels = False
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    for index, _ in enumerate(values):
        pie.slices[index].fillColor = _PALETTE[index % len(_PALETTE)]
    drawing.add(pie)
    return drawing


def _build_bar_drawing(title: str, labels: list[str], values: list[float], color: colors.Color, width: float = 245, height: float = 165):
    drawing = Drawing(width, height)
    drawing.add(String(width / 2, height - 12, title, fontName="Helvetica-Bold", fontSize=10, textAnchor="middle"))
    if not labels or not values:
        drawing.add(String(width / 2, height / 2, "No data for this period.", fontName="Helvetica", fontSize=9, textAnchor="middle", fillColor=colors.HexColor("#6b7280")))
        return drawing

    chart = VerticalBarChart()
    chart.x = 30
    chart.y = 20
    chart.width = width - 45
    chart.height = height - 48
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.dy = -8
    chart.categoryAxis.labels.fillColor = colors.HexColor("#6b7280")
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values) * 1.2 if max(values) > 0 else 1
    chart.valueAxis.valueStep = max(1, chart.valueAxis.valueMax / 5)
    chart.valueAxis.labels.fontSize = 6
    chart.valueAxis.labels.fillColor = colors.HexColor("#6b7280")
    chart.bars[0].fillColor = color
    chart.bars[0].strokeColor = color
    drawing.add(chart)
    return drawing


def _pair_table(left, right):
    table = Table([[left, right]], colWidths=[92 * mm, 92 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _report_period_label(period: str, start_date, end_date) -> str:
    if period == "week":
        return f"Weekly Report - {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
    if period == "month":
        return f"Monthly Report - {start_date.strftime('%B %Y')}"
    if period == "year":
        return f"Yearly Report - {start_date.strftime('%Y')}"
    return f"Report - {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"


def _build_visual_elements(period: str, income_items, expense_items, start_date, end_date, styles):
    income_frame = _frame_from_items(income_items)
    expense_frame = _frame_from_items(expense_items)
    start_day = _as_date(start_date)
    end_day = _as_date(end_date)

    income_categories = []
    income_category_values = []
    expense_categories = []
    expense_category_values = []

    if not income_frame.empty and "category_name" in income_frame.columns:
        grouped = income_frame.groupby("category_name")["amount"].sum().sort_values(ascending=False)
        income_categories = grouped.index.tolist()
        income_category_values = [float(value) for value in grouped.values.tolist()]

    if not expense_frame.empty and "category_name" in expense_frame.columns:
        grouped = expense_frame.groupby("category_name")["amount"].sum().sort_values(ascending=False)
        expense_categories = grouped.index.tolist()
        expense_category_values = [float(value) for value in grouped.values.tolist()]

    elements = [Paragraph("Visual Insights Summary", styles["SectionHeading"]), Spacer(1, 4)]
    elements.append(_pair_table(
        _build_pie_drawing("Income - Category Distribution", income_categories, income_category_values),
        _build_pie_drawing("Expense - Category Distribution", expense_categories, expense_category_values),
    ))
    elements.append(Spacer(1, 8))

    if period == "week":
        day_income_labels, day_income_values = _series_by_day(income_frame, start_day, end_day)
        day_expense_labels, day_expense_values = _series_by_day(expense_frame, start_day, end_day)
        elements.append(_pair_table(
            _build_bar_drawing("Income - Day-wise", day_income_labels, day_income_values, colors.HexColor("#10b981")),
            _build_bar_drawing("Expense - Day-wise", day_expense_labels, day_expense_values, colors.HexColor("#ef4444")),
        ))
    elif period == "month":
        day_income_labels, day_income_values = _series_by_day(income_frame, start_day, end_day)
        day_expense_labels, day_expense_values = _series_by_day(expense_frame, start_day, end_day)
        week_income_labels, week_income_values = _series_by_week(income_frame, start_day, end_day)
        week_expense_labels, week_expense_values = _series_by_week(expense_frame, start_day, end_day)
        elements.append(_pair_table(
            _build_bar_drawing("Income - Day-wise", day_income_labels, day_income_values, colors.HexColor("#10b981")),
            _build_bar_drawing("Expense - Day-wise", day_expense_labels, day_expense_values, colors.HexColor("#ef4444")),
        ))
        elements.append(Spacer(1, 8))
        elements.append(_pair_table(
            _build_bar_drawing("Income - Week-wise", week_income_labels, week_income_values, colors.HexColor("#2563eb")),
            _build_bar_drawing("Expense - Week-wise", week_expense_labels, week_expense_values, colors.HexColor("#f59e0b")),
        ))
    else:
        month_income_labels, month_income_values = _series_by_month(income_frame, start_day, end_day)
        month_expense_labels, month_expense_values = _series_by_month(expense_frame, start_day, end_day)
        elements.append(_pair_table(
            _build_bar_drawing("Income - Month-wise", month_income_labels, month_income_values, colors.HexColor("#10b981")),
            _build_bar_drawing("Expense - Month-wise", month_expense_labels, month_expense_values, colors.HexColor("#ef4444")),
        ))

    return elements


def _transaction_rows(user_id: str, start_date, end_date):
    expenses = list_expenses(user_id, start_date, end_date)
    income = list_income(user_id, start_date, end_date)
    rows = []
    for item in income:
        rows.append({**item, "type": "Income"})
    for item in expenses:
        rows.append({**item, "type": "Expense"})
    rows.sort(key=lambda row: row.get("date"), reverse=True)
    return rows


def report_summary(user_id: str, start_date, end_date):
    expenses = pd.DataFrame(list_expenses(user_id, start_date, end_date))
    income = pd.DataFrame(list_income(user_id, start_date, end_date))
    total_income = float(income["amount"].sum()) if not income.empty else 0.0
    total_expense = float(expenses["amount"].sum()) if not expenses.empty else 0.0
    net = total_income - total_expense

    def _extreme(df, top: bool = True):
        if df.empty or "category_name" not in df.columns:
            return "N/A"
        grouped = df.groupby("category_name")["amount"].sum()
        if grouped.empty:
            return "N/A"
        return str(grouped.idxmax() if top else grouped.idxmin())

    def _top_day(df, top: bool = True):
        if df.empty or "date" not in df.columns:
            return "N/A"
        frame = df.copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
        frame = frame.dropna(subset=["date"])
        if frame.empty:
            return "N/A"
        grouped = frame.groupby("date")["amount"].sum()
        if grouped.empty:
            return "N/A"
        return str(grouped.idxmax() if top else grouped.idxmin())

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net,
        "highest_income_category": _extreme(income, True),
        "lowest_income_category": _extreme(income, False),
        "highest_expense_category": _extreme(expenses, True),
        "lowest_expense_category": _extreme(expenses, False),
        "highest_income_date": _top_day(income, True),
        "highest_expense_date": _top_day(expenses, True),
    }


def build_pdf_report(user: dict, title: str, period: str, start_date, end_date, user_id: str) -> BytesIO:
    summary = report_summary(user_id, start_date, end_date)
    wallets = list_wallets(user_id)
    transactions = _transaction_rows(user_id, start_date, end_date)
    report_label = _report_period_label(period, start_date, end_date)

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], textColor=colors.HexColor("#1f2937"), spaceAfter=6))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=12))

    elements = [Paragraph("FinTrack INR Financial Report", styles["Title"]), Spacer(1, 6)]
    elements.append(Paragraph(report_label, styles["Heading2"]))
    elements.append(Paragraph(f"Date Generated: {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}", styles["BodySmall"]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("User Information", styles["SectionHeading"]))
    user_table = Table([["Name", user["name"]], ["Email", user["email"]]], colWidths=[48 * mm, 110 * mm])
    user_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5eef8"))]))
    elements.append(user_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Report Summary", styles["SectionHeading"]))
    summary_table = Table([["Total Income", f"₹ {summary['total_income']:.2f}"], ["Total Expenses", f"₹ {summary['total_expense']:.2f}"], ["Net Savings", f"₹ {summary['net_savings']:.2f}"]], colWidths=[64 * mm, 94 * mm])
    summary_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6"))]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Wallet Balances", styles["SectionHeading"]))
    wallet_rows = [["Wallet", "Type", "Current Balance"]]
    for wallet in wallets:
        wallet_rows.append([wallet["wallet_name"], wallet["wallet_type"], f"₹ {float(wallet.get('current_balance', 0)):.2f}"])
    wallet_table = Table(wallet_rows, repeatRows=1, colWidths=[60 * mm, 50 * mm, 48 * mm])
    wallet_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey)]))
    elements.append(wallet_table)
    elements.append(PageBreak())

    elements.append(Paragraph("Complete Transaction Table", styles["SectionHeading"]))
    tx_rows = [["Date", "Type", "Wallet", "Category", "Title", "Description", "Amount"]]
    for tx in transactions:
        tx_rows.append([
            tx.get("date").strftime("%d-%m-%Y") if tx.get("date") else "",
            tx.get("type", ""),
            tx.get("wallet_name", ""),
            tx.get("category_name", ""),
            tx.get("title", ""),
            tx.get("description", ""),
            f"₹ {float(tx.get('amount', 0)):.2f}",
        ])
    tx_table = Table(tx_rows, repeatRows=1, colWidths=[18 * mm, 18 * mm, 24 * mm, 24 * mm, 32 * mm, 44 * mm, 20 * mm])
    tx_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.2, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 7)]))
    elements.append(tx_table)
    elements.append(PageBreak())

    elements.append(Paragraph("Analytics Summary", styles["SectionHeading"]))
    analytics_table = Table([["Highest Income Category", summary["highest_income_category"]], ["Highest Expense Category", summary["highest_expense_category"]], ["Highest Income Date", summary["highest_income_date"]], ["Highest Expense Date", summary["highest_expense_date"]], ["Lowest Income Category", summary["lowest_income_category"]], ["Lowest Expense Category", summary["lowest_expense_category"]]], colWidths=[68 * mm, 90 * mm])
    analytics_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff"))]))
    elements.append(analytics_table)
    elements.append(Spacer(1, 10))

    elements.extend(_build_visual_elements(period, list_income(user_id, start_date, end_date), list_expenses(user_id, start_date, end_date), start_date, end_date, styles))

    document.build(elements)
    buffer.seek(0)
    return buffer
