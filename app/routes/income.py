from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import get_db
from app.forms import DeleteForm, IncomeForm
from app.services.finance_service import create_income, delete_income, list_categories, list_income, list_wallets, update_income


income_bp = Blueprint("income", __name__, url_prefix="/income")


def _populate_form(form: IncomeForm, user_id: str) -> None:
    wallets = list_wallets(user_id)
    categories = list_categories(user_id, "income")
    form.wallet_id.choices = [(str(wallet["_id"]), f"{wallet['wallet_name']} ({wallet['wallet_type']})") for wallet in wallets]
    form.category_id.choices = [(str(category["_id"]), category["name"]) for category in categories]


@income_bp.route("")
@login_required
def index():
    income_items = list_income(current_user.id)
    return render_template("transactions/income/index.html", income_items=income_items, delete_form=DeleteForm())


@income_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = IncomeForm()
    _populate_form(form, current_user.id)
    if form.validate_on_submit():
        try:
            create_income(current_user.id, form.wallet_id.data, form.category_id.data, form.title.data, form.description.data or "", form.amount.data, datetime.combine(form.date.data, datetime.min.time(), tzinfo=timezone.utc))
            flash("Income added.", "success")
            return redirect(url_for("income.index"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("transactions/income/form.html", form=form, title="Add Income")


@income_bp.route("/<income_id>/edit", methods=["GET", "POST"])
@login_required
def edit(income_id: str):
    income_item = get_db().income.find_one({"_id": ObjectId(income_id), "user_id": current_user.id})
    if not income_item:
        flash("Income not found.", "danger")
        return redirect(url_for("income.index"))
    form = IncomeForm()
    _populate_form(form, current_user.id)
    if request.method == "GET":
        form.wallet_id.data = income_item.get("wallet_id")
        form.category_id.data = income_item.get("category_id")
        form.amount.data = income_item.get("amount")
        form.title.data = income_item.get("title")
        form.description.data = income_item.get("description")
        if income_item.get("date"):
            form.date.data = income_item["date"].date()
    if form.validate_on_submit():
        try:
            update_income(current_user.id, income_id, form.wallet_id.data, form.category_id.data, form.title.data, form.description.data or "", form.amount.data, datetime.combine(form.date.data, datetime.min.time(), tzinfo=timezone.utc))
            flash("Income updated.", "success")
            return redirect(url_for("income.index"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("transactions/income/form.html", form=form, title="Edit Income")


@income_bp.route("/<income_id>/delete", methods=["POST"])
@login_required
def delete(income_id: str):
    form = DeleteForm()
    if form.validate_on_submit():
        try:
            delete_income(current_user.id, income_id)
            flash("Income deleted.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("income.index"))
