/**
 * static/js/main.js — Utilitários globais do Job Assistant IA.
 *
 * Fornece:
 *   - authFetch()   → Fetch autenticado com JWT automático e redirect no 401
 *   - showToast()   → Exibe notificações toast temporárias
 *   - escHtml()     → Escapa HTML para exibição segura
 *   - formatDate()  → Formata datas ISO para pt-BR
 */

// ── JWT Token Management ─────────────────────────────────────────────────────

/** Recupera o JWT token do localStorage. */
function getToken() {
  return localStorage.getItem('access_token') || '';
}

/** Fetch autenticado: injeta Bearer token e redireciona para /login no 401. */
async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = options.headers instanceof Headers
    ? options.headers
    : new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Não define Content-Type para FormData (o browser faz isso automaticamente)
  if (!(options.body instanceof FormData) && !headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  const resp = await fetch(url, { ...options, headers });

  if (resp.status === 401) {
    // Token expirado ou inválido → limpa e redireciona
    localStorage.removeItem('access_token');
    localStorage.removeItem('usuario');
    await fetch('/session/clear', { method: 'POST' });
    window.location.href = '/login';
    return resp;
  }

  return resp;
}

// ── Toast Notifications ──────────────────────────────────────────────────────

/**
 * Exibe um toast de notificação temporário.
 * @param {string} message - Mensagem a exibir
 * @param {string} type - 'success' | 'danger' | 'warning' | 'info'
 */
function showToast(message, type = 'success') {
  const toastEl = document.getElementById('globalToast');
  const toastMsg = document.getElementById('toastMsg');
  if (!toastEl || !toastMsg) return;

  toastMsg.textContent = message;
  toastEl.className = `toast align-items-center border-0 text-bg-${type}`;

  const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 4000 });
  toast.show();
}

// ── HTML Helpers ─────────────────────────────────────────────────────────────

/** Escapa caracteres especiais HTML para exibição segura. */
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/** Formata uma string de data ISO para exibição em pt-BR. */
function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleDateString('pt-BR', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  } catch {
    return isoStr;
  }
}
