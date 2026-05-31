from __future__ import annotations

from bson import ObjectId
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.forms import DeleteForm, WalletForm
from app.services.finance_service import create_wallet, delete_wallet, list_wallets, update_wallet
from config.constants import WALLET_TYPES


wallets_bp = Blueprint("wallets", __name__, url_prefix="/wallets")


@wallets_bp.route("")
@login_required
def index():
    wallets = list_wallets(current_user.id)
    return render_template("wallets/index.html", wallets=wallets, delete_form=DeleteForm())


@wallets_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = WalletForm()
    if form.validate_on_submit():
        create_wallet(current_user.id, form.wallet_name.data, form.wallet_type.data, form.opening_balance.data)
        flash("Wallet created successfully.", "success")
        return redirect(url_for("wallets.index"))
    return render_template("wallets/form.html", form=form, title="Add Wallet")


@wallets_bp.route("/<wallet_id>/edit", methods=["GET", "POST"])
@login_required
def edit(wallet_id: str):
    wallet = next((item for item in list_wallets(current_user.id) if str(item["_id"]) == wallet_id), None)
    if not wallet:
        flash("Wallet not found.", "danger")
        return redirect(url_for("wallets.index"))
    form = WalletForm(obj=wallet)
    if request.method == "GET":
        form.wallet_name.data = wallet.get("wallet_name")
        form.wallet_type.data = wallet.get("wallet_type")
        form.opening_balance.data = wallet.get("opening_balance", 0)
    if form.validate_on_submit():
        update_wallet(current_user.id, wallet_id, form.wallet_name.data, form.wallet_type.data, form.opening_balance.data)
        flash("Wallet updated.", "success")
        return redirect(url_for("wallets.index"))
    return render_template("wallets/form.html", form=form, title="Edit Wallet")


@wallets_bp.route("/<wallet_id>/delete", methods=["POST"])
@login_required
def delete(wallet_id: str):
    form = DeleteForm()
    if form.validate_on_submit():
        try:
            delete_wallet(current_user.id, wallet_id)
            flash("Wallet deleted.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("wallets.index"))
