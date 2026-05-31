from __future__ import annotations

import bcrypt
import html
import re
import secrets
from decimal import Decimal, InvalidOperation


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,72}$")
TAG_PATTERN = re.compile(r"<[^>]*>")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_otp(length: int = 6) -> str:
    start = 10 ** (length - 1)
    end = (10**length) - 1
    return str(secrets.randbelow(end - start + 1) + start)


def password_is_strong(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password or ""))


def sanitize_text(value: str | None) -> str:
    if not value:
        return ""
    stripped = TAG_PATTERN.sub("", value)
    cleaned = html.unescape(stripped).strip()
    return re.sub(r"[\x00-\x1f\x7f]", "", cleaned)


def to_decimal(value: str | float | int | Decimal) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid amount") from None
