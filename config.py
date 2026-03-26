"""
config.py — Configurações centrais do Job Assistant IA.
Todas as configurações sensíveis são lidas de variáveis de ambiente
(arquivo .env para desenvolvimento, variáveis de sistema para produção).
"""
import os
from dotenv import load_dotenv

# Carrega o arquivo .env se existir
load_dotenv()


class Config:
    # ── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-please-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

    # ── Banco de Dados ───────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:root@localhost:3306/job_assistant'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-please-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 horas em segundos
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = False  # True em produção com HTTPS
    JWT_COOKIE_CSRF_PROTECT = False

    # ── Ollama (IA Local) ────────────────────────────────────────────────────
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '120'))
    OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3')

    # ── Upload de Arquivos ───────────────────────────────────────────────────
    _default_upload = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', _default_upload) or _default_upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
