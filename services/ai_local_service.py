"""
services/ai_local_service.py — Serviço de IA local com prompts de sistema rígidos.

Fluxo de integração com Ollama:
  1. extract_keywords()     → Análise da vaga: extrai keywords e calcula match_score
  2. generate_resume()      → Personaliza o currículo do usuário para a vaga
  3. generate_cover_letter() → Gera carta de apresentação profissional

Os prompts são construídos para forçar o modelo a devolver respostas
estruturadas e consistentes, especialmente JSON puro na extração de keywords.
"""
import json
import time
import re
from typing import Optional

from services.ollama_client import ollama_client
from models.repositories import ProcessingLogRepository

# ─── Prompts de Sistema ───────────────────────────────────────────────────────

SYSTEM_KEYWORD_EXTRACTION = """Você é um especialista em RH, análise de vagas e otimização de currículos para ATS (Applicant Tracking Systems).

Sua tarefa é analisar a descrição de uma vaga e o currículo de um candidato, depois retornar SOMENTE um objeto JSON válido.

REGRAS ABSOLUTAS:
1. Responda APENAS com JSON válido. Sem texto antes ou depois.
2. Não inclua markdown, blocos de código ou explicações.
3. Use aspas duplas para strings.
4. O match_score deve ser um número inteiro entre 0 e 100.

FORMATO EXATO esperado:
{
  "keywords": ["python", "flask", "sql", "docker"],
  "match_score": 75,
  "required_skills": ["python", "sql"],
  "missing_skills": ["kubernetes"],
  "analysis": "O candidato tem forte base em Python e SQL. Falta experiência com Kubernetes."
}"""

SYSTEM_RESUME_GENERATION = """Você é um redator especialista em currículos profissionais e otimização para ATS (Applicant Tracking Systems).

Sua tarefa é reescrever e personalizar o currículo fornecido para a vaga específica.

DIRETRIZES:
- Use as palabras-chave da vaga naturalmente ao longo do currículo
- Destaque experiências e habilidades mais relevantes para a posição
- Quantifique conquistas sempre que possível (ex: "aumentei a performance em 30%")
- Use verbos de ação no início de cada bullet point
- Mantenha formato profissional em Markdown com seções claras
- Não invente informações — trabalhe apenas com o que foi fornecido no currículo
- Adapte o objetivo/sumário para a vaga específica

ESTRUTURA DO CURRÍCULO:
# [Nome do Candidato]
[Contato | Email | LinkedIn | GitHub]

## Objetivo Profissional
[2-3 linhas alinhadas com a vaga]

## Experiência Profissional
### [Cargo] — [Empresa] | [Período]
- [Conquista quantificada]
- [Responsabilidade relevante]

## Habilidades Técnicas
[Organize por categorias relevantes à vaga]

## Formação Acadêmica
...

## Certificações e Cursos
...
"""

SYSTEM_COVER_LETTER = """Você é um escritor especialista em cartas de apresentação profissionais e persuasivas.

Sua tarefa é criar uma carta de apresentação personalizada conectando a experiência do candidato com a vaga desejada.

DIRETRIZES:
- Tom: Profissional, confiante e entusiasmado
- Tamanho: 3-4 parágrafos (não muito longo)
- Estrutura: Abertura impactante → Conexão experiência-vaga → Valor que agrega → CTA
- NÃO comece com "Prezado(a) Recrutador(a)," — seja mais específico se souber o nome da empresa
- Use palavras-chave da vaga naturalmente
- Destaque 2-3 conquistas específicas do candidato
- Finalize com call-to-action claro

FORMATO:
[Data]

[Empresa]
Setor de Recursos Humanos

Prezado(a) Time de Recrutamento [Empresa],

[Abertura com cargo e motivação]

[Experiência e conquistas relevantes]

[Conexão com a empresa e demonstração de interesse]

[CTA e fechamento]

Atenciosamente,
[Nome do Candidato]
"""


# ─── Funções principais ───────────────────────────────────────────────────────

def extract_keywords(job_description: str, base_resume_text: str,
                     model: str, usuario_id: Optional[int] = None) -> dict:
    """
    Usa IA para extrair keywords e calcular o match score entre a vaga e o currículo.

    Args:
        job_description:  Descrição completa da vaga
        base_resume_text: Texto extraído do currículo do usuário
        model:            Modelo Ollama a usar (ex: 'llama3')
        usuario_id:       ID do usuário (para log de telemetria)

    Returns:
        {
          'success': True,
          'keywords': ['python', 'flask', ...],
          'match_score': 78,
          'required_skills': [...],
          'missing_skills': [...],
          'analysis': 'Texto de análise...',
          'model': 'llama3',
          'tokens': 450,
          'elapsed': 8.3,
        }
    """
    # Constrói o prompt do usuário com os dados reais
    has_resume = bool(base_resume_text and base_resume_text.strip())

    prompt = f"""Analise a vaga abaixo e o currículo do candidato.

=== DESCRIÇÃO DA VAGA ===
{job_description[:3000]}

=== CURRÍCULO DO CANDIDATO ===
{base_resume_text[:2000] if has_resume else 'Currículo não fornecido. Analise apenas a vaga e retorne match_score: 0.'}

Retorne APENAS o JSON conforme especificado."""

    start = time.time()
    result = ollama_client.generate(
        model=model,
        prompt=prompt,
        system=SYSTEM_KEYWORD_EXTRACTION,
        temperature=0.1,  # Baixa temperatura para respostas mais consistentes
    )
    elapsed_ms = int((time.time() - start) * 1000)

    if not result['success']:
        # Registra falha no log de telemetria
        if usuario_id:
            ProcessingLogRepository.create(
                usuario_id=usuario_id,
                tipo_operacao='keyword_extraction',
                modelo=model,
                sucesso=False,
                erro_msg=result.get('error', ''),
            )
        return {'success': False, 'error': result.get('error', 'Erro na IA')}

    # Tenta parsear o JSON da resposta
    parsed = _parse_json_response(result['response'])
    if not parsed:
        # Extração de fallback: retorna keywords vazias e score 0
        parsed = {
            'keywords': [],
            'match_score': 0,
            'required_skills': [],
            'missing_skills': [],
            'analysis': 'Não foi possível analisar automaticamente.'
        }

    # Registra sucesso na telemetria
    if usuario_id:
        ProcessingLogRepository.create(
            usuario_id=usuario_id,
            tipo_operacao='keyword_extraction',
            modelo=model,
            tokens_usados=result.get('tokens', 0),
            tempo_ms=elapsed_ms,
            sucesso=True,
        )

    return {
        'success': True,
        'keywords':       parsed.get('keywords', []),
        'match_score':    _clamp_score(parsed.get('match_score', 0)),
        'required_skills': parsed.get('required_skills', []),
        'missing_skills': parsed.get('missing_skills', []),
        'analysis':       parsed.get('analysis', ''),
        'model':          result.get('model', model),
        'tokens':         result.get('tokens', 0),
        'elapsed':        result.get('elapsed', 0),
    }


def generate_resume(base_resume_text: str, job_description: str,
                    job_title: str, company: str, keywords: list,
                    model: str, usuario_id: Optional[int] = None) -> dict:
    """
    Gera um currículo personalizado para a vaga usando IA local.

    Args:
        base_resume_text: Texto do currículo base do usuário
        job_description:  Descrição da vaga
        job_title:        Título da vaga
        company:          Nome da empresa
        keywords:         Lista de keywords extraídas da vaga
        model:            Modelo Ollama
        usuario_id:       Para telemetria

    Returns:
        {'success': True, 'conteudo': '...', 'tokens': N, 'elapsed': X.X}
    """
    if not base_resume_text:
        return {'success': False, 'error': 'Currículo base não encontrado. Faça o upload do seu currículo primeiro.'}

    keywords_str = ', '.join(keywords[:20]) if keywords else 'não identificadas'

    prompt = f"""Personalize o currículo abaixo para a seguinte vaga.

=== VAGA TARGET ===
Posição: {job_title}
Empresa: {company or 'Não informada'}
Keywords importantes da vaga: {keywords_str}

=== DESCRIÇÃO DA VAGA ===
{job_description[:2500]}

=== CURRÍCULO ORIGINAL DO CANDIDATO ===
{base_resume_text[:3000]}

Gere o currículo personalizado em Markdown seguindo as diretrizes do sistema."""

    start = time.time()
    result = ollama_client.generate(
        model=model,
        prompt=prompt,
        system=SYSTEM_RESUME_GENERATION,
        temperature=0.6,
    )
    elapsed_ms = int((time.time() - start) * 1000)

    success = result.get('success', False)

    # Registra telemetria
    if usuario_id:
        ProcessingLogRepository.create(
            usuario_id=usuario_id,
            tipo_operacao='resume_generation',
            modelo=model,
            tokens_usados=result.get('tokens', 0),
            tempo_ms=elapsed_ms,
            sucesso=success,
            erro_msg=result.get('error') if not success else None,
        )

    if not success:
        return {'success': False, 'error': result.get('error', 'Erro na geração do currículo')}

    return {
        'success': True,
        'conteudo': result['response'],
        'tokens':   result.get('tokens', 0),
        'elapsed':  result.get('elapsed', 0),
        'model':    result.get('model', model),
    }


def generate_cover_letter(base_resume_text: str, job_description: str,
                          job_title: str, company: str,
                          model: str, usuario_id: Optional[int] = None) -> dict:
    """
    Gera uma carta de apresentação profissional para a vaga.

    Returns:
        {'success': True, 'conteudo': '...', 'tokens': N, 'elapsed': X.X}
    """
    if not base_resume_text:
        return {'success': False, 'error': 'Currículo base não encontrado. Faça o upload do seu currículo primeiro.'}

    prompt = f"""Crie uma carta de apresentação para a vaga abaixo.

=== VAGA ===
Posição: {job_title}
Empresa: {company or 'Não informada'}

=== DESCRIÇÃO DA VAGA ===
{job_description[:2000]}

=== INFORMAÇÕES DO CANDIDATO (do currículo) ===
{base_resume_text[:2000]}

Crie a carta seguindo as diretrizes do sistema."""

    start = time.time()
    result = ollama_client.generate(
        model=model,
        prompt=prompt,
        system=SYSTEM_COVER_LETTER,
        temperature=0.75,
    )
    elapsed_ms = int((time.time() - start) * 1000)

    success = result.get('success', False)

    if usuario_id:
        ProcessingLogRepository.create(
            usuario_id=usuario_id,
            tipo_operacao='cover_letter',
            modelo=model,
            tokens_usados=result.get('tokens', 0),
            tempo_ms=elapsed_ms,
            sucesso=success,
            erro_msg=result.get('error') if not success else None,
        )

    if not success:
        return {'success': False, 'error': result.get('error', 'Erro na geração da cover letter')}

    return {
        'success': True,
        'conteudo': result['response'],
        'tokens':   result.get('tokens', 0),
        'elapsed':  result.get('elapsed', 0),
        'model':    result.get('model', model),
    }


# ─── Utilitários internos ─────────────────────────────────────────────────────

def _parse_json_response(text: str) -> Optional[dict]:
    """
    Extrai e parseia JSON de uma resposta de LLM.
    LLMs às vezes envolvem o JSON em markdown code blocks — remove esses wrappers.
    """
    if not text:
        return None

    # Remove blocos de markdown se existirem
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Tenta parsear diretamente
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tenta extrair o primeiro objeto JSON válido da string
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _clamp_score(score) -> float:
    """Garante que o score esteja entre 0 e 100."""
    try:
        return round(min(100.0, max(0.0, float(score))), 1)
    except (TypeError, ValueError):
        return 0.0
