"""
api/auth_routes.py — Endpoints de autenticação documentados com Flask-RESTx.

Namespace: /api/auth
  POST /register       → Cria um novo usuário
  POST /login          → Retorna JWT access token
  POST /upload-resume  → Upload do currículo base (PDF/DOCX)
  GET  /profile        → Dados do usuário logado
"""
from flask import request, current_app
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)

from extensions import bcrypt, db
from models.repositories import UsuarioRepository
from services.resume_processor import process_upload

auth_ns = Namespace('auth', description='Autenticação e gestão de usuários', path='/auth')

# ── Modelos para o Swagger ────────────────────────────────────────────────────
register_model = auth_ns.model('Register', {
    'nome':  fields.String(required=True, description='Nome completo', example='João Silva'),
    'email': fields.String(required=True, description='E-mail único', example='joao@email.com'),
    'senha': fields.String(required=True, description='Senha (mín. 6 caracteres)', example='senha123'),
    'preferencia_modelo_ia': fields.String(
        description='Modelo Ollama preferido', example='llama3',
        enum=['llama3', 'mistral', 'gemma:2b']
    ),
})

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, example='joao@email.com'),
    'senha': fields.String(required=True, example='senha123'),
})

token_response = auth_ns.model('TokenResponse', {
    'access_token': fields.String(description='JWT Bearer token'),
    'usuario':      fields.Raw(description='Dados do usuário'),
})

error_model = auth_ns.model('Error', {
    'error': fields.String(description='Mensagem de erro'),
})


# ── Endpoints ─────────────────────────────────────────────────────────────────
@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model, validate=True)
    @auth_ns.response(201, 'Usuário criado com sucesso', token_response)
    @auth_ns.response(400, 'Dados inválidos', error_model)
    @auth_ns.response(409, 'E-mail já cadastrado', error_model)
    def post(self):
        """Registra um novo usuário no sistema."""
        data = request.get_json()

        email = data.get('email', '').strip().lower()
        nome  = data.get('nome', '').strip()
        senha = data.get('senha', '')
        modelo = data.get('preferencia_modelo_ia', 'llama3')

        # Validações básicas
        if not email or not nome or not senha:
            return {'error': 'Nome, e-mail e senha são obrigatórios.'}, 400
        if len(senha) < 6:
            return {'error': 'A senha deve ter no mínimo 6 caracteres.'}, 400
        if UsuarioRepository.email_exists(email):
            return {'error': 'Este e-mail já está cadastrado.'}, 409

        # Hash da senha com Bcrypt
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        usuario = UsuarioRepository.create(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            preferencia_modelo_ia=modelo,
        )

        access_token = create_access_token(identity=str(usuario.id))
        return {
            'access_token': access_token,
            'usuario': usuario.to_dict(),
        }, 201


@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model, validate=True)
    @auth_ns.response(200, 'Login realizado', token_response)
    @auth_ns.response(401, 'Credenciais inválidas', error_model)
    def post(self):
        """Autentica o usuário e retorna um JWT token."""
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        senha = data.get('senha', '')

        usuario = UsuarioRepository.get_by_email(email)
        if not usuario or not bcrypt.check_password_hash(usuario.senha_hash, senha):
            return {'error': 'E-mail ou senha incorretos.'}, 401

        access_token = create_access_token(identity=str(usuario.id))
        return {
            'access_token': access_token,
            'usuario': usuario.to_dict(),
        }, 200


@auth_ns.route('/profile')
class Profile(Resource):
    @jwt_required()
    @auth_ns.response(200, 'Perfil do usuário')
    @auth_ns.response(401, 'Token inválido ou expirado', error_model)
    def get(self):
        """Retorna os dados do usuário autenticado."""
        user_id = int(get_jwt_identity())
        usuario = UsuarioRepository.get_by_id(user_id)
        if not usuario:
            return {'error': 'Usuário não encontrado.'}, 404
        return usuario.to_dict(), 200

    @jwt_required()
    @auth_ns.response(200, 'Perfil atualizado')
    def put(self):
        """Atualiza preferências do usuário."""
        user_id = int(get_jwt_identity())
        usuario = UsuarioRepository.get_by_id(user_id)
        if not usuario:
            return {'error': 'Usuário não encontrado.'}, 404

        data = request.get_json() or {}
        allowed = {'nome', 'preferencia_modelo_ia'}
        update_data = {k: v for k, v in data.items() if k in allowed}

        if update_data:
            UsuarioRepository.update(usuario, **update_data)
        return usuario.to_dict(), 200


@auth_ns.route('/upload-resume')
class UploadResume(Resource):
    @jwt_required()
    @auth_ns.response(200, 'Currículo enviado com sucesso')
    @auth_ns.response(400, 'Arquivo inválido', error_model)
    def post(self):
        """Faz upload do currículo base (PDF ou DOCX) e extrai o texto."""
        user_id = int(get_jwt_identity())
        usuario = UsuarioRepository.get_by_id(user_id)
        if not usuario:
            return {'error': 'Usuário não encontrado.'}, 404

        if 'arquivo' not in request.files:
            return {'error': 'Nenhum arquivo enviado. Use o campo "arquivo".'}, 400

        file = request.files['arquivo']
        result = process_upload(file)

        if not result['success']:
            return {'error': result['error']}, 400

        # Atualiza o usuário com o caminho e texto do currículo
        UsuarioRepository.update(
            usuario,
            curriculo_base_path=result['filepath'],
            curriculo_base_texto=result['texto'],
        )

        return {
            'message': 'Currículo enviado e processado com sucesso!',
            'filename': result['filename'],
            'num_chars': result['num_chars'],
        }, 200
