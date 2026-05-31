from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import get_db
from app.forms import DeleteForm, ExpenseForm
from app.services.finance_service import create_expense, delete_expense, list_categories, list_expenses, list_wallets, update_expense


expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


def _populate_form(form: ExpenseForm, user_id: str) -> None:
    wallets = list_wallets(user_id)
    categories = list_categories(user_id, "expense")
    form.wallet_id.choices = [(str(wallet["_id"]), f"{wallet['wallet_name']} ({wallet['wallet_type']})") for wallet in wallets]
    form.category_id.choices = [(str(category["_id"]), category["name"]) for category in categories]


@expenses_bp.route("")
@login_required
def index():
    expenses = list_expenses(current_user.id)
    return render_template("transactions/expenses/index.html", expenses=expenses, delete_form=DeleteForm())


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = ExpenseForm()
    _populate_form(form, current_user.id)
    if form.validate_on_submit():
        try:
            create_expense(current_user.id, form.wallet_id.data, form.category_id.data, form.title.data, form.description.data or "", form.amount.data, datetime.combine(form.date.data, datetime.min.time(), tzinfo=timezone.utc))
            flash("Expense added.", "success")
            return redirect(url_for("expenses.index"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("transactions/expenses/form.html", form=form, title="Add Expense")


@expenses_bp.route("/<expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id: str):
    expense = get_db().expenses.find_one({"_id": ObjectId(expense_id), "user_id": current_user.id})
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("expenses.index"))
    form = ExpenseForm()
    _populate_form(form, current_user.id)
    if request.method == "GET":
        form.wallet_id.data = expense.get("wallet_id")
        form.category_id.data = expense.get("category_id")
        form.amount.data = expense.get("amount")
        form.title.data = expense.get("title")
        form.description.data = expense.get("description")
        if expense.get("date"):
            form.date.data = expense["date"].date()
    if form.validate_on_submit():
        try:
            update_expense(current_user.id, expense_id, form.wallet_id.data, form.category_id.data, form.title.data, form.description.data or "", form.amount.data, datetime.combine(form.date.data, datetime.min.time(), tzinfo=timezone.utc))
            flash("Expense updated.", "success")
            return redirect(url_for("expenses.index"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("transactions/expenses/form.html", form=form, title="Edit Expense")


@expenses_bp.route("/<expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id: str):
    form = DeleteForm()
    if form.validate_on_submit():
        try:
            delete_expense(current_user.id, expense_id)
            flash("Expense deleted.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("expenses.index"))
