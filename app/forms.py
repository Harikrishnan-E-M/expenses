from __future__ import annotations

from datetime import date

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DecimalField, HiddenField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError

from config.constants import WALLET_TYPES
from app.utils.security import password_is_strong


class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=72)])
    submit = SubmitField("Send OTP")

    def validate_password(self, field):
        if not password_is_strong(field.data):
            raise ValidationError("Password must be at least 8 characters and include upper, lower, digit, and special character.")


class VerifyOtpForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    otp = StringField("OTP", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Verify OTP")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=72)])
    submit = SubmitField("Login")


class WalletForm(FlaskForm):
    wallet_name = StringField("Wallet Name", validators=[DataRequired(), Length(min=2, max=80)])
    wallet_type = SelectField("Wallet Type", choices=[(wallet_type, wallet_type) for wallet_type in WALLET_TYPES], validators=[DataRequired()])
    opening_balance = DecimalField("Opening Balance", places=2, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Save Wallet")


class CategoryForm(FlaskForm):
    category_type = SelectField("Category Type", choices=[("expense", "Expense"), ("income", "Income")], validators=[DataRequired()])
    name = StringField("Category Name", validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField("Save Category")


class ExpenseForm(FlaskForm):
    wallet_id = SelectField("Wallet", validators=[DataRequired()])
    category_id = SelectField("Category", validators=[DataRequired()])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    title = StringField("Title", validators=[DataRequired(), Length(min=2, max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    submit = SubmitField("Save Expense")


class IncomeForm(FlaskForm):
    wallet_id = SelectField("Wallet", validators=[DataRequired()])
    category_id = SelectField("Category", validators=[DataRequired()])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    title = StringField("Title", validators=[DataRequired(), Length(min=2, max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    date = DateField("Date", default=date.today, validators=[DataRequired()])
    submit = SubmitField("Save Income")


class ReportFilterForm(FlaskForm):
    period = SelectField(
        "Period",
        choices=[("week", "Week"), ("month", "Month"), ("year", "Year")],
        validators=[DataRequired()],
    )
    range_value = StringField("Range", validators=[Optional()])
    submit = SubmitField("Generate Report")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired(), Length(min=8, max=72)])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8, max=72)])
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")])
    submit = SubmitField("Update Password")

    def validate_new_password(self, field):
        if not password_is_strong(field.data):
            raise ValidationError("Password must be at least 8 characters and include upper, lower, digit, and special character.")


class DeleteAccountForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=72)])
    confirm = BooleanField("I understand this permanently deletes my account and financial records", validators=[DataRequired()])
    submit = SubmitField("Delete Account")


class DeleteForm(FlaskForm):
    confirm = BooleanField("Confirm deletion", validators=[DataRequired()])
    submit = SubmitField("Delete")


class HiddenActionForm(FlaskForm):
    item_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Confirm")
