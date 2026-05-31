from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
from bson import ObjectId

from config.constants import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES, WALLET_TYPES
from app.extensions import get_db
from app.utils.security import sanitize_text, to_decimal


def _wallets():
    return get_db().wallets


def _expenses():
    return get_db().expenses


def _income():
    return get_db().income


def _expense_categories():
    return get_db().expense_categories


def _income_categories():
    return get_db().income_categories


def _category_collection(category_type: str):
    if category_type == "expense":
        return _expense_categories()
    if category_type == "income":
        return _income_categories()
    raise ValueError("Invalid category type")


def _wallet_lookup(user_id: str) -> dict[str, dict]:
    wallets = _wallets().find({"user_id": user_id})
    return {str(wallet["_id"]): wallet for wallet in wallets}


def _category_lookup(user_id: str, category_type: str) -> dict[str, dict]:
    collection = _category_collection(category_type)
    categories = collection.find({"user_id": user_id})
    return {str(category["_id"]): category for category in categories}


def _decorate_transactions(user_id: str, documents: list[dict], category_type: str) -> list[dict]:
    wallets = _wallet_lookup(user_id)
    categories = _category_lookup(user_id, category_type)
    decorated = []
    for document in documents:
        category = categories.get(str(document.get("category_id")), {})
        wallet = wallets.get(str(document.get("wallet_id")), {})
        decorated.append(
            {
                **document,
                "wallet_name": wallet.get("wallet_name", ""),
                "wallet_type": wallet.get("wallet_type", ""),
                "category_name": category.get("name", ""),
            }
        )
    return decorated


def seed_default_categories(user_id: str) -> None:
    now = datetime.now(timezone.utc)
    for name in DEFAULT_EXPENSE_CATEGORIES:
        _expense_categories().update_one(
            {"user_id": user_id, "name": name},
            {"$setOnInsert": {"user_id": user_id, "name": name, "created_at": now, "updated_at": now}},
            upsert=True,
        )
    for name in DEFAULT_INCOME_CATEGORIES:
        _income_categories().update_one(
            {"user_id": user_id, "name": name},
            {"$setOnInsert": {"user_id": user_id, "name": name, "created_at": now, "updated_at": now}},
            upsert=True,
        )


def _normalize_decimal(amount: str | float | int | Decimal) -> Decimal:
    return to_decimal(amount)


def create_wallet(user_id: str, wallet_name: str, wallet_type: str, opening_balance: str | float | int) -> str:
    now = datetime.now(timezone.utc)
    opening = _normalize_decimal(opening_balance)
    document = {
        "user_id": user_id,
        "wallet_name": sanitize_text(wallet_name),
        "wallet_type": wallet_type if wallet_type in WALLET_TYPES else "Other",
        "opening_balance": float(opening),
        "current_balance": float(opening),
        "created_at": now,
        "updated_at": now,
    }
    result = _wallets().insert_one(document)
    return str(result.inserted_id)


def update_wallet(user_id: str, wallet_id: str, wallet_name: str, wallet_type: str, opening_balance: str | float | int) -> None:
    wallet = _wallets().find_one({"_id": ObjectId(wallet_id), "user_id": user_id})
    if not wallet:
        raise ValueError("Wallet not found")
    opening = _normalize_decimal(opening_balance)
    difference = float(opening) - float(wallet.get("opening_balance", 0))
    _wallets().update_one(
        {"_id": wallet["_id"], "user_id": user_id},
        {
            "$set": {
                "wallet_name": sanitize_text(wallet_name),
                "wallet_type": wallet_type if wallet_type in WALLET_TYPES else "Other",
                "opening_balance": float(opening),
                "updated_at": datetime.now(timezone.utc),
            },
            "$inc": {"current_balance": difference},
        },
    )


def delete_wallet(user_id: str, wallet_id: str) -> None:
    wallet = _wallets().find_one({"_id": ObjectId(wallet_id), "user_id": user_id})
    if not wallet:
        raise ValueError("Wallet not found")
    if _expenses().find_one({"user_id": user_id, "wallet_id": wallet_id}) or _income().find_one({"user_id": user_id, "wallet_id": wallet_id}):
        raise ValueError("Wallet has transactions and cannot be deleted")
    _wallets().delete_one({"_id": wallet["_id"], "user_id": user_id})


def list_wallets(user_id: str):
    return list(_wallets().find({"user_id": user_id}).sort("created_at", -1))


def list_categories(user_id: str, category_type: str):
    collection = _category_collection(category_type)
    return list(collection.find({"user_id": user_id}).sort("name", 1))


def create_category(user_id: str, category_type: str, name: str) -> str:
    clean_name = sanitize_text(name)
    collection = _category_collection(category_type)
    if collection.find_one({"user_id": user_id, "name": clean_name}):
        raise ValueError("Category already exists")
    document = {"user_id": user_id, "name": clean_name, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
    return str(collection.insert_one(document).inserted_id)


def update_category(user_id: str, category_type: str, category_id: str, name: str) -> None:
    collection = _category_collection(category_type)
    document = collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
    if not document:
        raise ValueError("Category not found")
    collection.update_one({"_id": document["_id"], "user_id": user_id}, {"$set": {"name": sanitize_text(name), "updated_at": datetime.now(timezone.utc)}})


def delete_category(user_id: str, category_type: str, category_id: str) -> None:
    collection = _category_collection(category_type)
    if category_type == "expense" and _expenses().find_one({"user_id": user_id, "category_id": category_id}):
        raise ValueError("Category is used by expenses")
    if category_type == "income" and _income().find_one({"user_id": user_id, "category_id": category_id}):
        raise ValueError("Category is used by income")
    result = collection.delete_one({"_id": ObjectId(category_id), "user_id": user_id})
    if not result.deleted_count:
        raise ValueError("Category not found")


def _update_wallet_balance(user_id: str, wallet_id: str, delta: Decimal, session=None):
    collection = _wallets()
    collection.update_one({"_id": ObjectId(wallet_id), "user_id": user_id}, {"$inc": {"current_balance": float(delta)}, "$set": {"updated_at": datetime.now(timezone.utc)}}, session=session)


def create_expense(user_id: str, wallet_id: str, category_id: str, title: str, description: str, amount: str | float | int, expense_date: datetime) -> str:
    with get_db().client.start_session() as session:
        with session.start_transaction():
            wallet = _wallets().find_one({"_id": ObjectId(wallet_id), "user_id": user_id}, session=session)
            if not wallet:
                raise ValueError("Wallet not found")
            amount_dec = _normalize_decimal(amount)
            if amount_dec <= 0:
                raise ValueError("Amount must be greater than zero")
            document = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "category_id": category_id,
                "title": sanitize_text(title),
                "description": sanitize_text(description),
                "amount": float(amount_dec),
                "date": expense_date,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            result = _expenses().insert_one(document, session=session)
            _update_wallet_balance(user_id, wallet_id, Decimal(str(-float(amount_dec))), session=session)
            return str(result.inserted_id)


def update_expense(user_id: str, expense_id: str, wallet_id: str, category_id: str, title: str, description: str, amount: str | float | int, expense_date: datetime) -> None:
    with get_db().client.start_session() as session:
        with session.start_transaction():
            existing = _expenses().find_one({"_id": ObjectId(expense_id), "user_id": user_id}, session=session)
            if not existing:
                raise ValueError("Expense not found")
            amount_dec = _normalize_decimal(amount)
            if amount_dec <= 0:
                raise ValueError("Amount must be greater than zero")
            old_amount = Decimal(str(existing["amount"]))
            old_wallet_id = existing["wallet_id"]
            if old_wallet_id == wallet_id:
                delta = old_amount - amount_dec
                _update_wallet_balance(user_id, wallet_id, delta, session=session)
            else:
                _update_wallet_balance(user_id, old_wallet_id, old_amount, session=session)
                _update_wallet_balance(user_id, wallet_id, Decimal(str(-float(amount_dec))), session=session)
            _expenses().update_one(
                {"_id": existing["_id"], "user_id": user_id},
                {
                    "$set": {
                        "wallet_id": wallet_id,
                        "category_id": category_id,
                        "title": sanitize_text(title),
                        "description": sanitize_text(description),
                        "amount": float(amount_dec),
                        "date": expense_date,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                session=session,
            )


def delete_expense(user_id: str, expense_id: str) -> None:
    with get_db().client.start_session() as session:
        with session.start_transaction():
            existing = _expenses().find_one({"_id": ObjectId(expense_id), "user_id": user_id}, session=session)
            if not existing:
                raise ValueError("Expense not found")
            _update_wallet_balance(user_id, existing["wallet_id"], Decimal(str(existing["amount"])), session=session)
            _expenses().delete_one({"_id": existing["_id"], "user_id": user_id}, session=session)


def create_income(user_id: str, wallet_id: str, category_id: str, title: str, description: str, amount: str | float | int, income_date: datetime) -> str:
    with get_db().client.start_session() as session:
        with session.start_transaction():
            wallet = _wallets().find_one({"_id": ObjectId(wallet_id), "user_id": user_id}, session=session)
            if not wallet:
                raise ValueError("Wallet not found")
            amount_dec = _normalize_decimal(amount)
            if amount_dec <= 0:
                raise ValueError("Amount must be greater than zero")
            document = {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "category_id": category_id,
                "title": sanitize_text(title),
                "description": sanitize_text(description),
                "amount": float(amount_dec),
                "date": income_date,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            result = _income().insert_one(document, session=session)
            _update_wallet_balance(user_id, wallet_id, amount_dec, session=session)
            return str(result.inserted_id)


def update_income(user_id: str, income_id: str, wallet_id: str, category_id: str, title: str, description: str, amount: str | float | int, income_date: datetime) -> None:
    with get_db().client.start_session() as session:
        with session.start_transaction():
            existing = _income().find_one({"_id": ObjectId(income_id), "user_id": user_id}, session=session)
            if not existing:
                raise ValueError("Income not found")
            amount_dec = _normalize_decimal(amount)
            if amount_dec <= 0:
                raise ValueError("Amount must be greater than zero")
            old_amount = Decimal(str(existing["amount"]))
            old_wallet_id = existing["wallet_id"]
            if old_wallet_id == wallet_id:
                delta = amount_dec - old_amount
                _update_wallet_balance(user_id, wallet_id, delta, session=session)
            else:
                _update_wallet_balance(user_id, old_wallet_id, Decimal(str(-float(old_amount))), session=session)
                _update_wallet_balance(user_id, wallet_id, amount_dec, session=session)
            _income().update_one(
                {"_id": existing["_id"], "user_id": user_id},
                {
                    "$set": {
                        "wallet_id": wallet_id,
                        "category_id": category_id,
                        "title": sanitize_text(title),
                        "description": sanitize_text(description),
                        "amount": float(amount_dec),
                        "date": income_date,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                session=session,
            )


def delete_income(user_id: str, income_id: str) -> None:
    with get_db().client.start_session() as session:
        with session.start_transaction():
            existing = _income().find_one({"_id": ObjectId(income_id), "user_id": user_id}, session=session)
            if not existing:
                raise ValueError("Income not found")
            _update_wallet_balance(user_id, existing["wallet_id"], Decimal(str(-float(existing["amount"]))), session=session)
            _income().delete_one({"_id": existing["_id"], "user_id": user_id}, session=session)


def list_expenses(user_id: str, start_date=None, end_date=None):
    query = {"user_id": user_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    documents = list(_expenses().find(query).sort("date", -1))
    return _decorate_transactions(user_id, documents, "expense")


def list_income(user_id: str, start_date=None, end_date=None):
    query = {"user_id": user_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    documents = list(_income().find(query).sort("date", -1))
    return _decorate_transactions(user_id, documents, "income")


def aggregate_transactions(user_id: str, start_date=None, end_date=None):
    expenses = pd.DataFrame(list_expenses(user_id, start_date, end_date))
    income = pd.DataFrame(list_income(user_id, start_date, end_date))
    if not expenses.empty:
        expenses["amount"] = expenses["amount"].astype(float)
    if not income.empty:
        income["amount"] = income["amount"].astype(float)
    return expenses, income


def current_user_wallet_total(user_id: str) -> float:
    wallets = list(_wallets().find({"user_id": user_id}, {"current_balance": 1}))
    balances = [float(wallet.get("current_balance", 0)) for wallet in wallets]
    return float(np.sum(balances)) if balances else 0.0


def current_day_range():
    today = datetime.now(timezone.utc).date()
    return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc), datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)


def dashboard_summary(user_id: str, start_date, end_date):
    expenses = list_expenses(user_id, start_date, end_date)
    income = list_income(user_id, start_date, end_date)
    income_total = float(sum(item.get("amount", 0) for item in income))
    expense_total = float(sum(item.get("amount", 0) for item in expenses))
    savings = income_total - expense_total
    today_start, today_end = current_day_range()
    return {
        "income_total": income_total,
        "expense_total": expense_total,
        "savings": savings,
        "wallet_total": current_user_wallet_total(user_id),
        "today_income": list_income(user_id, today_start, today_end),
        "today_expenses": list_expenses(user_id, today_start, today_end),
        "recent_expenses": expenses[:5],
        "recent_income": income[:5],
        "wallets": list_wallets(user_id),
    }


def category_distribution(items, label_field: str = "category_name"):
    if not items:
        return [], []
    frame = pd.DataFrame(items)
    if label_field not in frame.columns:
        return [], []
    grouped = frame.groupby(label_field)["amount"].sum().sort_values(ascending=False)
    labels = grouped.index.tolist()
    values = grouped.values.tolist()
    return labels, values


def date_series(items):
    if not items:
        return [], []
    frame = pd.DataFrame(items)
    if "date" not in frame.columns:
        return [], []
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    grouped = frame.groupby("date")["amount"].sum().sort_index()
    return [str(value) for value in grouped.index.tolist()], grouped.values.tolist()


def day_series(items):
    """Aggregate items by calendar day. Returns (labels, values)."""
    if not items:
        return [], []
    frame = pd.DataFrame(items)
    if "date" not in frame.columns:
        return [], []
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    grouped = frame.groupby("date")["amount"].sum().sort_index()
    labels = [d.strftime("%a %d %b") for d in grouped.index]
    return labels, [round(float(v), 2) for v in grouped.values]


def week_series(items):
    """Aggregate items by Sunday-start week. Returns (labels, values)."""
    if not items:
        return [], []
    frame = pd.DataFrame(items)
    if "date" not in frame.columns:
        return [], []
    frame["date"] = pd.to_datetime(frame["date"])
    # Week starts on Sunday (subtract weekday+1 mod 7 days)
    frame["week_start"] = frame["date"].apply(
        lambda d: (d - pd.Timedelta(days=(d.weekday() + 1) % 7)).date()
    )
    grouped = frame.groupby("week_start")["amount"].sum().sort_index()
    labels = [
        f"{ws.strftime('%d %b')} – {(ws + pd.Timedelta(days=6)).strftime('%d %b')}"
        for ws in grouped.index
    ]
    return labels, [round(float(v), 2) for v in grouped.values]


def month_series(items):
    """Aggregate items by calendar month. Returns (labels, values)."""
    if not items:
        return [], []
    frame = pd.DataFrame(items)
    if "date" not in frame.columns:
        return [], []
    frame["date"] = pd.to_datetime(frame["date"])
    frame["month"] = frame["date"].dt.to_period("M")
    grouped = frame.groupby("month")["amount"].sum().sort_index()
    labels = [p.strftime("%b %Y") for p in grouped.index]
    return labels, [round(float(v), 2) for v in grouped.values]


def get_earliest_transaction_date(user_id: str):
    """Return the earliest date found across all expenses and income for the user.

    Returns a :class:`datetime.date` or ``None`` if the user has no transactions.
    """
    from datetime import date as date_type

    candidates = []

    expense_doc = _expenses().find_one(
        {"user_id": user_id, "date": {"$exists": True}},
        {"date": 1},
        sort=[("date", 1)],
    )
    if expense_doc and expense_doc.get("date"):
        d = expense_doc["date"]
        candidates.append(d.date() if isinstance(d, datetime) else d)

    income_doc = _income().find_one(
        {"user_id": user_id, "date": {"$exists": True}},
        {"date": 1},
        sort=[("date", 1)],
    )
    if income_doc and income_doc.get("date"):
        d = income_doc["date"]
        candidates.append(d.date() if isinstance(d, datetime) else d)

    if not candidates:
        return None
    return min(candidates)
