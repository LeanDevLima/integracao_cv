"""
services/ollama_client.py — Cliente HTTP para a API local do Ollama.

O Ollama expõe uma API REST em http://localhost:11434.
Este módulo abstrai as chamadas HTTP, gerenciando timeouts,
erros de conexão e formatos de resposta.

Endpoints utilizados:
  POST /api/generate  → Gera texto a partir de um prompt
  GET  /api/tags      → Lista modelos disponíveis
  GET  /              → Health check
"""
import requests
import json
import time
from flask import current_app


class OllamaClient:
    """Cliente para a API REST do servidor Ollama local."""

    def __init__(self):
        # A URL base e o timeout são lidos da config do Flask
        self.base_url = None
        self.timeout = None

    def _get_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        try:
            return current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')
        except RuntimeError:
            # Fora do contexto Flask (testes)
            return 'http://localhost:11434'

    def _get_timeout(self) -> int:
        if self.timeout:
            return self.timeout
        try:
            return current_app.config.get('OLLAMA_TIMEOUT', 120)
        except RuntimeError:
            return 120

    # ── Health check ──────────────────────────────────────────────────────────
    def check_health(self) -> dict:
        """
        Verifica se o servidor Ollama está rodando.
        Retorna {'online': True/False, 'message': '...'}
        """
        try:
            resp = requests.get(
                f"{self._get_base_url()}/",
                timeout=5
            )
            if resp.status_code == 200:
                return {'online': True, 'message': 'Ollama está online'}
            return {'online': False, 'message': f'HTTP {resp.status_code}'}
        except requests.exceptions.ConnectionError:
            return {'online': False, 'message': 'Conexão recusada. Ollama não está rodando.'}
        except requests.exceptions.Timeout:
            return {'online': False, 'message': 'Timeout ao conectar com o Ollama.'}
        except Exception as e:
            return {'online': False, 'message': str(e)}

    # ── Listar modelos disponíveis ─────────────────────────────────────────────
    def list_models(self) -> dict:
        """
        Busca os modelos instalados no servidor Ollama.
        Retorna {'success': True, 'models': [...]} ou {'success': False, 'error': '...'}
        """
        try:
            resp = requests.get(
                f"{self._get_base_url()}/api/tags",
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            models = [
                {
                    'name': m.get('name', ''),
                    'size': m.get('size', 0),
                    'modified_at': m.get('modified_at', ''),
                }
                for m in data.get('models', [])
            ]
            return {'success': True, 'models': models}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Ollama não está acessível', 'models': []}
        except requests.exceptions.HTTPError as e:
            return {'success': False, 'error': f'Erro HTTP: {e}', 'models': []}
        except Exception as e:
            return {'success': False, 'error': str(e), 'models': []}

    # ── Geração de texto (core) ───────────────────────────────────────────────
    def generate(self, model: str, prompt: str, system: str = None,
                 temperature: float = 0.7, max_retries: int = 1) -> dict:
        """
        Envia um prompt para o Ollama e aguarda a resposta completa (sem streaming).

        Args:
            model:       Nome do modelo (ex: 'llama3', 'mistral', 'gemma:2b')
            prompt:      Conteúdo do prompt do usuário
            system:      Prompt de sistema (instrução de comportamento)
            temperature: Temperatura de geração (0.0 = determinístico, 1.0 = criativo)
            max_retries: Tentativas em caso de falha

        Returns:
            {
              'success': True,
              'response': '<texto gerado>',
              'model': '<model usado>',
              'tokens': <total tokens>,
              'elapsed': <segundos>,
            }
            ou
            {
              'success': False,
              'error': '<mensagem>'
            }
        """
        payload = {
            'model': model,
            'prompt': prompt,
            'stream': False,         # Recebe resposta completa de uma vez
            'options': {
                'temperature': temperature,
                'num_predict': 4096,  # máximo de tokens gerados
            }
        }
        if system:
            payload['system'] = system

        url = f"{self._get_base_url()}/api/generate"
        timeout = self._get_timeout()

        for attempt in range(max_retries + 1):
            try:
                start = time.time()
                resp = requests.post(url, json=payload, timeout=timeout)
                elapsed = time.time() - start

                resp.raise_for_status()
                data = resp.json()

                # A resposta do Ollama pode vir como stream ou completa
                # Com stream=False, vem em um único objeto JSON
                response_text = data.get('response', '')
                tokens = (
                    data.get('eval_count', 0) +
                    data.get('prompt_eval_count', 0)
                )

                return {
                    'success': True,
                    'response': response_text,
                    'model': data.get('model', model),
                    'tokens': tokens,
                    'elapsed': round(elapsed, 2),
                    'done': data.get('done', True),
                }

            except requests.exceptions.ConnectionError:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return {
                    'success': False,
                    'error': 'Não foi possível conectar ao Ollama. Verifique se está rodando.'
                }
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    continue
                return {
                    'success': False,
                    'error': f'Timeout após {timeout}s. Tente um modelo menor ou aumente OLLAMA_TIMEOUT.'
                }
            except requests.exceptions.HTTPError as e:
                return {'success': False, 'error': f'Erro HTTP do Ollama: {e}'}
            except json.JSONDecodeError:
                return {'success': False, 'error': 'Resposta inválida do Ollama (não é JSON).'}
            except Exception as e:
                return {'success': False, 'error': f'Erro inesperado: {str(e)}'}

        return {'success': False, 'error': 'Falha após todas as tentativas.'}


# Instância singleton para uso no app
ollama_client = OllamaClient()
