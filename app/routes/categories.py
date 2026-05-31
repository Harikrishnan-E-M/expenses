from __future__ import annotations

from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import get_db
from app.forms import CategoryForm, DeleteForm
from app.services.finance_service import create_category, delete_category, list_categories, update_category


categories_bp = Blueprint("categories", __name__, url_prefix="/categories")


@categories_bp.route("")
@login_required
def index():
    expense_categories = list_categories(current_user.id, "expense")
    income_categories = list_categories(current_user.id, "income")
    form = CategoryForm()
    return render_template("categories/index.html", expense_categories=expense_categories, income_categories=income_categories, form=form, delete_form=DeleteForm())


@categories_bp.route("/new", methods=["POST"])
@login_required
def new():
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            create_category(current_user.id, form.category_type.data, form.name.data)
            flash("Category created successfully.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("categories.index"))


@categories_bp.route("/<category_type>/<category_id>/edit", methods=["GET", "POST"])
@login_required
def edit(category_type: str, category_id: str):
    form = CategoryForm()
    collection = get_db().expense_categories if category_type == "expense" else get_db().income_categories
    category = collection.find_one({"_id": ObjectId(category_id), "user_id": current_user.id})
    if not category:
        flash("Category not found.", "danger")
        return redirect(url_for("categories.index"))
    if request.method == "GET":
        form.category_type.data = category_type
        form.name.data = category.get("name")
    if form.validate_on_submit():
        try:
            update_category(current_user.id, category_type, category_id, form.name.data)
            flash("Category updated.", "success")
            return redirect(url_for("categories.index"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("categories/edit.html", form=form, category_type=category_type, category=category)


@categories_bp.route("/<category_type>/<category_id>/delete", methods=["POST"])
@login_required
def delete(category_type: str, category_id: str):
    form = DeleteForm()
    if form.validate_on_submit():
        try:
            delete_category(current_user.id, category_type, category_id)
            flash("Category deleted.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("categories.index"))
