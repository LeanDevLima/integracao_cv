"""
api/web_routes.py — Blueprint para as páginas Jinja2 do frontend.
Serve as páginas HTML que usam o JWT armazenado no localStorage
para fazer chamadas autenticadas à API REST via Fetch.
"""
from flask import Blueprint, render_template, redirect, url_for, request, session

web_bp = Blueprint('web', __name__, template_folder='../templates')


def _is_logged_in() -> bool:
    """Verifica se há token na sessão do Flask."""
    return 'access_token' in session


# ── Rota raiz ─────────────────────────────────────────────────────────────────
@web_bp.route('/')
def index():
    if not _is_logged_in():
        return redirect(url_for('web.login'))
    return redirect(url_for('web.jobs_list'))


# ── Autenticação ──────────────────────────────────────────────────────────────
@web_bp.route('/login', methods=['GET'])
def login():
    if _is_logged_in():
        return redirect(url_for('web.jobs_list'))
    return render_template('auth/login.html')


@web_bp.route('/register', methods=['GET'])
def register():
    if _is_logged_in():
        return redirect(url_for('web.jobs_list'))
    return render_template('auth/register.html')


@web_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('web.login'))


# Endpoint interno: chamado pelo JS após login bem-sucedido para salvar sessão
@web_bp.route('/session/set', methods=['POST'])
def set_session():
    data = request.get_json()
    if data and 'access_token' in data:
        session['access_token'] = data['access_token']
        session['usuario'] = data.get('usuario', {})
        return {'ok': True}, 200
    return {'error': 'Token não fornecido'}, 400


@web_bp.route('/session/clear', methods=['POST'])
def clear_session():
    session.clear()
    return {'ok': True}, 200


# ── Vagas ─────────────────────────────────────────────────────────────────────
@web_bp.route('/jobs')
def jobs_list():
    if not _is_logged_in():
        return redirect(url_for('web.login'))
    usuario = session.get('usuario', {})
    return render_template('jobs/list.html', usuario=usuario)


@web_bp.route('/jobs/<int:vaga_id>')
def job_detail(vaga_id):
    if not _is_logged_in():
        return redirect(url_for('web.login'))
    usuario = session.get('usuario', {})
    return render_template('jobs/detail.html', vaga_id=vaga_id, usuario=usuario)


# ── Documentos ────────────────────────────────────────────────────────────────
@web_bp.route('/documents')
def documents():
    if not _is_logged_in():
        return redirect(url_for('web.login'))
    usuario = session.get('usuario', {})
    return render_template('documents/index.html', usuario=usuario)


# ── Perfil ────────────────────────────────────────────────────────────────────
@web_bp.route('/profile')
def profile():
    if not _is_logged_in():
        return redirect(url_for('web.login'))
    usuario = session.get('usuario', {})
    return render_template('auth/profile.html', usuario=usuario)
