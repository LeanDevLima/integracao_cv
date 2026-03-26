"""
run.py — Ponto de entrada do Job Assistant IA.

Usa o padrão Application Factory para criar e configurar o app Flask,
registrar todos os namespaces Flask-RESTx (Swagger) e inicializar o banco.

Acesse o Swagger em: http://localhost:5000/api/docs
"""
import os
from flask import Flask
from flask_restx import Api

from config import Config
from extensions import db, jwt, bcrypt


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Inicializa extensões ──────────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # Garante que o diretório de uploads existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Flask-RESTx: Swagger UI em /api/docs ──────────────────────────────────
    api = Api(
        app,
        version='1.0',
        title='Job Assistant IA API',
        description=(
            'API REST para personalização de currículos e cartas de apresentação '
            'com IA local (Ollama). Autentique-se com /api/auth/login e use o '
            'token JWT no formato: Bearer <token>'
        ),
        doc='/api/docs',      # URL do Swagger UI
        prefix='/api',        # Prefixo de todas as rotas da API
        authorizations={
            'Bearer': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Insira: Bearer {seu_token_jwt}'
            }
        },
        security='Bearer',    # Aplica segurança por padrão a todos os endpoints
    )

    # ── Registra os namespaces da API ─────────────────────────────────────────
    from api.auth_routes import auth_ns
    from api.job_routes import jobs_ns
    from api.ollama_routes import ollama_ns

    api.add_namespace(auth_ns)
    api.add_namespace(jobs_ns)
    api.add_namespace(ollama_ns)

    # ── Registra o blueprint web (páginas Jinja2) ─────────────────────────────
    from api.web_routes import web_bp
    app.register_blueprint(web_bp)

    # ── Cria as tabelas do banco na primeira execução ─────────────────────────
    with app.app_context():
        db.create_all()
        print("✅ Tabelas verificadas/criadas com sucesso.")

    return app


# Cria a instância do app para uso com gunicorn ou flask CLI
app = create_app()

if __name__ == '__main__':
    print("🚀 Job Assistant IA iniciando...")
    print("📖 Swagger UI: http://localhost:5000/api/docs")
    print("🌐 Interface Web: http://localhost:5000")
    app.run(debug=app.config.get('DEBUG', True), host='0.0.0.0', port=5000)
