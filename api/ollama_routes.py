"""
api/ollama_routes.py — Endpoints para status e gestão do servidor Ollama.

Namespace: /api/ollama
  GET /status  → Verifica se Ollama está online e lista modelos
  GET /models  → Lista modelos com detalhes
"""
from flask_restx import Namespace, Resource, fields
from services.ollama_client import ollama_client

ollama_ns = Namespace('ollama', description='Status e modelos do servidor Ollama', path='/ollama')

# ── Modelos para o Swagger ────────────────────────────────────────────────────
status_model = ollama_ns.model('OllamaStatus', {
    'online':  fields.Boolean(description='Servidor está online'),
    'message': fields.String(description='Mensagem de status'),
    'models':  fields.List(fields.Raw, description='Modelos disponíveis'),
})

model_item = ollama_ns.model('ModelItem', {
    'name':        fields.String(description='Nome do modelo'),
    'size':        fields.Integer(description='Tamanho em bytes'),
    'modified_at': fields.String(description='Data de modificação'),
})


# ── Endpoints ─────────────────────────────────────────────────────────────────
@ollama_ns.route('/status')
class OllamaStatus(Resource):
    @ollama_ns.response(200, 'Status do servidor Ollama', status_model)
    def get(self):
        """
        Verifica se o servidor Ollama está rodando e retorna os modelos disponíveis.
        Usado pelo frontend para o polling de status (badge na topbar).
        """
        health = ollama_client.check_health()
        models_info = []

        if health['online']:
            models_result = ollama_client.list_models()
            if models_result['success']:
                models_info = models_result['models']

        return {
            'online':  health['online'],
            'message': health['message'],
            'models':  models_info,
            'num_models': len(models_info),
        }, 200


@ollama_ns.route('/models')
class OllamaModels(Resource):
    @ollama_ns.response(200, 'Lista de modelos instalados')
    @ollama_ns.response(503, 'Ollama não está disponível')
    def get(self):
        """Lista todos os modelos instalados no servidor Ollama com detalhes."""
        result = ollama_client.list_models()

        if not result['success']:
            return {
                'error': result.get('error', 'Ollama não disponível'),
                'models': []
            }, 503

        return {
            'models': result['models'],
            'total':  len(result['models']),
        }, 200
