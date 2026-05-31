from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bson import ObjectId
from flask_login import UserMixin

from app.extensions import get_db


@dataclass
class UserDocument:
    id: str
    name: str
    email: str
    password_hash: str
    verified: bool
    created_at: datetime
    updated_at: datetime


class User(UserMixin):
    def __init__(self, document: dict):
        self.id = str(document["_id"])
        self.name = document["name"]
        self.email = document["email"]
        self.password_hash = document["password_hash"]
        self.verified = document.get("verified", False)
        self.created_at = document.get("created_at")
        self.updated_at = document.get("updated_at")

    @staticmethod
    def from_id(user_id: str) -> "User | None":
        document = get_db().users.find_one({"_id": ObjectId(user_id)})
        return User(document) if document else None

    @staticmethod
    def by_email(email: str) -> "User | None":
        document = get_db().users.find_one({"email": email.lower().strip()})
        return User(document) if document else None


def serialize_user(document: dict) -> dict:
    return {
        "_id": str(document["_id"]),
        "name": document["name"],
        "email": document["email"],
        "verified": document.get("verified", False),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }
