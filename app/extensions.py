from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_pymongo import PyMongo
from flask_wtf import CSRFProtect
from flask import current_app


mongo = PyMongo()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def get_db():
	return mongo.cx[current_app.config["MONGO_DBNAME"]]
