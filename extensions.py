"""
extensions.py — Instâncias compartilhadas das extensões Flask.
São inicializadas aqui (sem app) e vinculadas ao app em run.py
via o padrão Application Factory, evitando importações circulares.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
