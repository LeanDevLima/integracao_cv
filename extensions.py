"""
extensions.py — Instâncias compartilhadas das extensões Flask.
São inicializadas aqui (sem app) e vinculadas ao app em run.py
via o padrão Application Factory, evitando importações circulares.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
