from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import get_db
from app.models.user import User
from app.services.email_service import send_otp_email
from app.services.finance_service import seed_default_categories
from app.utils.security import generate_otp, hash_password, verify_password


def _otp_collection():
    return get_db().otp_verifications


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_registration_otp(name: str, email: str, password: str) -> None:
    normalized_email = email.lower().strip()
    otp = generate_otp(current_app.config["OTP_LENGTH"])
    otp_doc = {
        "purpose": "registration",
        "name": name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(password),
        "otp_hash": hash_password(otp),
        "verified": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=current_app.config["OTP_EXPIRY_MINUTES"]),
        "attempts": 0,
    }
    _otp_collection().delete_many({"purpose": "registration", "email": normalized_email, "verified": False})
    inserted_id = _otp_collection().insert_one(otp_doc).inserted_id
    try:
        send_otp_email(name, normalized_email, otp)
    except ValueError:
        _otp_collection().delete_one({"_id": inserted_id})
        raise


def verify_registration_otp(email: str, otp: str) -> User:
    normalized_email = email.lower().strip()
    otp_doc = _otp_collection().find_one({"purpose": "registration", "email": normalized_email, "verified": False})
    if not otp_doc:
        raise ValueError("OTP request not found")
    expires_at = _as_utc(otp_doc["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        _otp_collection().delete_one({"_id": otp_doc["_id"]})
        raise ValueError("OTP expired")
    if otp_doc["attempts"] >= 5:
        raise ValueError("Too many OTP attempts")
    if not verify_password(otp, otp_doc["otp_hash"]):
        _otp_collection().update_one({"_id": otp_doc["_id"]}, {"$inc": {"attempts": 1}})
        raise ValueError("Invalid OTP")

    db = get_db()
    existing_user = db.users.find_one({"email": normalized_email})
    if existing_user:
        _otp_collection().delete_one({"_id": otp_doc["_id"]})
        raise ValueError("Account already exists")

    user_doc = {
        "name": otp_doc["name"],
        "email": normalized_email,
        "password_hash": otp_doc["password_hash"],
        "verified": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    user_id = db.users.insert_one(user_doc).inserted_id
    seed_default_categories(str(user_id))
    _otp_collection().delete_one({"_id": otp_doc["_id"]})
    created_user = db.users.find_one({"_id": user_id})
    return User(created_user)
