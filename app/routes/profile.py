from __future__ import annotations

from bson import ObjectId
from datetime import datetime, timezone
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, logout_user

from app.extensions import get_db
from app.forms import ChangePasswordForm, DeleteAccountForm
from app.utils.security import hash_password, verify_password


profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


def _delete_user_data(user_id: str) -> None:
    collections = ["wallets", "expenses", "income", "expense_categories", "income_categories", "otp_verifications"]
    db = get_db()
    for collection_name in collections:
        db[collection_name].delete_many({"user_id": user_id})
    db.otp_verifications.delete_many({"email": current_user.email})
    db.users.delete_one({"_id": ObjectId(user_id)})


@profile_bp.route("")
@login_required
def index():
    change_password_form = ChangePasswordForm()
    delete_account_form = DeleteAccountForm()
    return render_template("profile/index.html", change_password_form=change_password_form, delete_account_form=delete_account_form)


@profile_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user_document = get_db().users.find_one({"_id": ObjectId(current_user.id)})
        if not user_document or not verify_password(form.current_password.data, user_document["password_hash"]):
            flash("Current password is incorrect.", "danger")
        else:
            get_db().users.update_one(
                {"_id": user_document["_id"]},
                {"$set": {"password_hash": hash_password(form.new_password.data), "updated_at": datetime.now(timezone.utc)}},
            )
            flash("Password updated successfully.", "success")
    else:
        flash("Unable to update password. Please check the inputs.", "danger")
    return redirect(url_for("profile.index"))


@profile_bp.route("/delete", methods=["POST"])
@login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        user_document = get_db().users.find_one({"_id": ObjectId(current_user.id)})
        if not user_document or not verify_password(form.password.data, user_document["password_hash"]):
            flash("Password confirmation failed.", "danger")
        else:
            _delete_user_data(current_user.id)
            logout_user()
            flash("Your account and all associated records have been deleted.", "success")
            return redirect(url_for("auth.login"))
    else:
        flash("Account deletion requires confirmation.", "danger")
    return redirect(url_for("profile.index"))
