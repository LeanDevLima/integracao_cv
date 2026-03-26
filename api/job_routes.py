"""
api/job_routes.py — Endpoints de vagas e geração de documentos com IA.

Namespace: /api/jobs (todos protegidos por JWT)
  GET  /              → Lista vagas do usuário
  POST /              → Cria nova vaga
  GET  /<id>          → Detalhes da vaga
  DELETE /<id>        → Remove vaga
  POST /<id>/analyze  → Analisa vaga com IA (keywords + match_score)
  POST /<id>/generate-resume       → Gera currículo personalizado
  POST /<id>/generate-cover-letter → Gera carta de apresentação
  GET  /<id>/documents → Lista documentos gerados para a vaga
"""
from flask import request, current_app
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.repositories import (
    VagaRepository, UsuarioRepository,
    CurriculoGeradoRepository, CoverLetterGeradaRepository, KeywordRepository
)
from services import ai_local_service

jobs_ns = Namespace('jobs', description='Gestão de vagas e geração de documentos com IA', path='/jobs')

# ── Modelos para o Swagger ────────────────────────────────────────────────────
vaga_create_model = jobs_ns.model('VagaCreate', {
    'titulo':             fields.String(required=True, example='Desenvolvedor Python Sênior'),
    'empresa':            fields.String(example='TechCorp Ltda'),
    'descricao_completa': fields.String(required=True, example='Buscamos desenvolvedor Python com experiência em Flask...'),
})

vaga_response = jobs_ns.model('VagaResponse', {
    'id':                      fields.Integer,
    'titulo':                  fields.String,
    'empresa':                 fields.String,
    'match_score':             fields.Float,
    'status':                  fields.String,
    'palavras_chave_extraidas': fields.List(fields.String),
    'created_at':              fields.String,
})

generate_model = jobs_ns.model('GenerateRequest', {
    'modelo': fields.String(
        description='Modelo Ollama a usar. Se omitido, usa a preferência do usuário.',
        example='llama3',
        enum=['llama3', 'mistral', 'gemma:2b']
    ),
})

error_model = jobs_ns.model('Error', {
    'error': fields.String(),
})


def _get_user(user_id_str: str):
    """Helper: busca o usuário pelo ID do JWT."""
    return UsuarioRepository.get_by_id(int(user_id_str))


def _resolve_model(data: dict, usuario) -> str:
    """Determina qual modelo usar: da requisição ou preferência do usuário."""
    modelo = data.get('modelo') if data else None
    return modelo or usuario.preferencia_modelo_ia or current_app.config.get('OLLAMA_DEFAULT_MODEL', 'llama3')


# ── CRUD de Vagas ─────────────────────────────────────────────────────────────
@jobs_ns.route('/')
class VagaList(Resource):
    @jwt_required()
    @jobs_ns.response(200, 'Lista de vagas')
    def get(self):
        """Lista todas as vagas do usuário autenticado."""
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        paginated = VagaRepository.list_by_user(int(user_id), page=page, per_page=per_page)
        return {
            'vagas':   [v.to_dict() for v in paginated.items],
            'total':   paginated.total,
            'page':    paginated.page,
            'pages':   paginated.pages,
        }, 200

    @jwt_required()
    @jobs_ns.expect(vaga_create_model, validate=True)
    @jobs_ns.response(201, 'Vaga criada', vaga_response)
    @jobs_ns.response(400, 'Dados inválidos', error_model)
    def post(self):
        """Cria uma nova vaga para análise."""
        user_id = get_jwt_identity()
        data = request.get_json()

        titulo = data.get('titulo', '').strip()
        descricao = data.get('descricao_completa', '').strip()
        empresa = data.get('empresa', '').strip()

        if not titulo or not descricao:
            return {'error': 'Título e descrição são obrigatórios.'}, 400
        if len(descricao) < 50:
            return {'error': 'Descrição muito curta. Forneça a descrição completa da vaga.'}, 400

        vaga = VagaRepository.create(
            usuario_id=int(user_id),
            titulo=titulo,
            descricao_completa=descricao,
            empresa=empresa,
        )
        return vaga.to_dict(), 201


@jobs_ns.route('/<int:vaga_id>')
class VagaDetail(Resource):
    @jwt_required()
    @jobs_ns.response(200, 'Detalhes da vaga', vaga_response)
    @jobs_ns.response(404, 'Vaga não encontrada', error_model)
    def get(self, vaga_id):
        """Retorna os detalhes completos de uma vaga."""
        user_id = get_jwt_identity()
        vaga = VagaRepository.get_by_id(vaga_id)

        if not vaga or vaga.usuario_id != int(user_id):
            return {'error': 'Vaga não encontrada.'}, 404

        return vaga.to_dict(), 200

    @jwt_required()
    @jobs_ns.response(204, 'Vaga removida')
    @jobs_ns.response(404, 'Vaga não encontrada', error_model)
    def delete(self, vaga_id):
        """Remove uma vaga e todos os documentos gerados para ela."""
        user_id = get_jwt_identity()
        vaga = VagaRepository.get_by_id(vaga_id)

        if not vaga or vaga.usuario_id != int(user_id):
            return {'error': 'Vaga não encontrada.'}, 404

        VagaRepository.delete(vaga)
        return '', 204


# ── Análise com IA ────────────────────────────────────────────────────────────
@jobs_ns.route('/<int:vaga_id>/analyze')
class AnalisarVaga(Resource):
    @jwt_required()
    @jobs_ns.expect(generate_model)
    @jobs_ns.response(200, 'Análise concluída')
    @jobs_ns.response(404, 'Vaga não encontrada', error_model)
    @jobs_ns.response(503, 'Ollama indisponível', error_model)
    def post(self, vaga_id):
        """
        Analisa a vaga com IA:
        - Extrai keywords técnicas da descrição
        - Calcula o match score comparando com o currículo do usuário
        - Salva os resultados na vaga

        Esta operação pode levar de 10 a 60 segundos dependendo do modelo.
        """
        user_id = get_jwt_identity()
        usuario = _get_user(user_id)
        if not usuario:
            return {'error': 'Usuário não encontrado.'}, 404

        vaga = VagaRepository.get_by_id(vaga_id)
        if not vaga or vaga.usuario_id != int(user_id):
            return {'error': 'Vaga não encontrada.'}, 404

        data = request.get_json(silent=True) or {}
        modelo = _resolve_model(data, usuario)

        # Chama o serviço de IA para extração de keywords
        result = ai_local_service.extract_keywords(
            job_description=vaga.descricao_completa,
            base_resume_text=usuario.curriculo_base_texto or '',
            model=modelo,
            usuario_id=int(user_id),
        )

        if not result['success']:
            return {'error': result.get('error', 'Erro na análise.')}, 503

        # Atualiza a vaga com os resultados da IA
        vaga = VagaRepository.update_analise(
            vaga,
            match_score=result['match_score'],
            keywords=result['keywords'],
            analise_resumo=result.get('analysis', ''),
        )

        # Associa keywords ao banco de dados
        if result['keywords']:
            keyword_objs = KeywordRepository.bulk_get_or_create(result['keywords'])
            vaga.keywords = keyword_objs
            from extensions import db
            db.session.commit()

        return {
            'message':         'Análise concluída com sucesso!',
            'match_score':     result['match_score'],
            'keywords':        result['keywords'],
            'required_skills': result.get('required_skills', []),
            'missing_skills':  result.get('missing_skills', []),
            'analysis':        result.get('analysis', ''),
            'model':           result.get('model', modelo),
            'tokens':          result.get('tokens', 0),
            'elapsed':         result.get('elapsed', 0),
        }, 200


# ── Geração de Currículo ──────────────────────────────────────────────────────
@jobs_ns.route('/<int:vaga_id>/generate-resume')
class GerarCurriculo(Resource):
    @jwt_required()
    @jobs_ns.expect(generate_model)
    @jobs_ns.response(201, 'Currículo gerado com sucesso')
    @jobs_ns.response(400, 'Currículo base não encontrado', error_model)
    @jobs_ns.response(503, 'Ollama indisponível', error_model)
    def post(self, vaga_id):
        """
        Gera um currículo personalizado para a vaga usando IA local.
        O usuário deve ter feito upload do currículo base via /api/auth/upload-resume.

        Esta operação pode levar de 30 a 120 segundos dependendo do modelo.
        """
        user_id = get_jwt_identity()
        usuario = _get_user(user_id)
        if not usuario:
            return {'error': 'Usuário não encontrado.'}, 404

        vaga = VagaRepository.get_by_id(vaga_id)
        if not vaga or vaga.usuario_id != int(user_id):
            return {'error': 'Vaga não encontrada.'}, 404

        if not usuario.curriculo_base_texto:
            return {'error': 'Você ainda não enviou seu currículo base. Acesse Perfil > Upload Currículo.'}, 400

        data = request.get_json(silent=True) or {}
        modelo = _resolve_model(data, usuario)

        import json as _json
        try:
            keywords = _json.loads(vaga.palavras_chave_extraidas or '[]')
        except Exception:
            keywords = []

        # Gera o currículo personalizado
        result = ai_local_service.generate_resume(
            base_resume_text=usuario.curriculo_base_texto,
            job_description=vaga.descricao_completa,
            job_title=vaga.titulo,
            company=vaga.empresa or '',
            keywords=keywords,
            model=modelo,
            usuario_id=int(user_id),
        )

        if not result['success']:
            return {'error': result.get('error', 'Erro na geração.')}, 503

        # Salva o currículo gerado no banco
        curriculo = CurriculoGeradoRepository.create(
            vaga_id=vaga_id,
            usuario_id=int(user_id),
            conteudo=result['conteudo'],
            modelo_ia_utilizado=result.get('model', modelo),
            tempo_inferencia=result.get('elapsed', 0),
            tokens=result.get('tokens', 0),
        )

        # Atualiza status da vaga
        VagaRepository.update(vaga, status='gerado')

        return {
            'message':   'Currículo gerado com sucesso!',
            'curriculo': curriculo.to_dict(),
        }, 201


# ── Geração de Cover Letter ───────────────────────────────────────────────────
@jobs_ns.route('/<int:vaga_id>/generate-cover-letter')
class GerarCoverLetter(Resource):
    @jwt_required()
    @jobs_ns.expect(generate_model)
    @jobs_ns.response(201, 'Cover letter gerada com sucesso')
    @jobs_ns.response(400, 'Currículo base não encontrado', error_model)
    @jobs_ns.response(503, 'Ollama indisponível', error_model)
    def post(self, vaga_id):
        """
        Gera uma carta de apresentação personalizada para a vaga usando IA local.
        Esta operação pode levar de 20 a 90 segundos dependendo do modelo.
        """
        user_id = get_jwt_identity()
        usuario = _get_user(user_id)
        if not usuario:
            return {'error': 'Usuário não encontrado.'}, 404

        vaga = VagaRepository.get_by_id(vaga_id)
        if not vaga or vaga.usuario_id != int(user_id):
            return {'error': 'Vaga não encontrada.'}, 404

        if not usuario.curriculo_base_texto:
            return {'error': 'Você ainda não enviou seu currículo base. Acesse Perfil > Upload Currículo.'}, 400

        data = request.get_json(silent=True) or {}
        modelo = _resolve_model(data, usuario)

        result = ai_local_service.generate_cover_letter(
            base_resume_text=usuario.curriculo_base_texto,
            job_description=vaga.descricao_completa,
            job_title=vaga.titulo,
            company=vaga.empresa or '',
            model=modelo,
            usuario_id=int(user_id),
        )

        if not result['success']:
            return {'error': result.get('error', 'Erro na geração.')}, 503

        cover = CoverLetterGeradaRepository.create(
            vaga_id=vaga_id,
            usuario_id=int(user_id),
            conteudo=result['conteudo'],
            modelo_ia_utilizado=result.get('model', modelo),
            tempo_inferencia=result.get('elapsed', 0),
            tokens=result.get('tokens', 0),
        )

        return {
            'message':      'Cover letter gerada com sucesso!',
            'cover_letter': cover.to_dict(),
        }, 201


# ── Documentos Gerados para uma Vaga ─────────────────────────────────────────
@jobs_ns.route('/<int:vaga_id>/documents')
class VagaDocuments(Resource):
    @jwt_required()
    @jobs_ns.response(200, 'Documentos gerados para a vaga')
    def get(self, vaga_id):
        """Lista todos os currículos e cover letters gerados para uma vaga específica."""
        user_id = get_jwt_identity()
        vaga = VagaRepository.get_by_id(vaga_id)
        if not vaga or vaga.usuario_id != int(user_id):
            return {'error': 'Vaga não encontrada.'}, 404

        curriculos = CurriculoGeradoRepository.list_by_vaga(vaga_id)
        covers = CoverLetterGeradaRepository.list_by_vaga(vaga_id)

        return {
            'vaga_id':       vaga_id,
            'curriculos':    [c.to_dict() for c in curriculos],
            'cover_letters': [c.to_dict() for c in covers],
        }, 200
