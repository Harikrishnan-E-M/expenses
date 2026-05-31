from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import limiter, get_db
from app.forms import LoginForm, RegistrationForm, VerifyOtpForm
from app.models.user import User
from app.services.otp_service import create_registration_otp, verify_registration_otp
from app.utils.security import hash_password, verify_password
from config.settings import Config


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(Config.REGISTER_LIMIT)
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            create_registration_otp(form.name.data, form.email.data, form.password.data)
            flash("OTP sent to your email. Verify it to complete registration.", "success")
            return redirect(url_for("auth.verify_otp", email=form.email.data))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
@limiter.limit(Config.OTP_VERIFY_LIMIT)
def verify_otp():
    email = request.args.get("email", "")
    pending = get_db().otp_verifications.find_one({"email": email.lower().strip(), "purpose": "registration", "verified": False}) if email else None
    form = VerifyOtpForm()
    if request.method == "GET" and pending:
        form.name.data = pending.get("name", "")
        form.email.data = email
    if form.validate_on_submit():
        try:
            user = verify_registration_otp(form.email.data, form.otp.data)
            login_user(user)
            flash("Account verified successfully.", "success")
            return redirect(url_for("dashboard.home"))
        except ValueError as exc:
            flash(str(exc), "danger")
    elif request.method == "GET" and email:
        form.email.data = email
    return render_template("auth/verify_otp.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(Config.LOGIN_LIMIT)
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_document = get_db().users.find_one({"email": form.email.data.lower().strip()})
        if not user_document or not verify_password(form.password.data, user_document["password_hash"]):
            flash("Invalid email or password.", "danger")
        elif not user_document.get("verified", False):
            flash("Please verify your account first.", "warning")
        else:
            login_user(User(user_document))
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard.home"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
