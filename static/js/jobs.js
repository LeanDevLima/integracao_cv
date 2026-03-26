/**
 * static/js/jobs.js — Funções JS específicas das páginas de vagas.
 * Incluído em jobs/list.html e jobs/detail.html.
 */

// Este arquivo atualmente serve como extensão — as funções principais
// já estão inline nos templates para facilitar o acesso a variáveis
// de contexto Jinja2 (como VAGA_ID).
// Funções auxiliares adicionais podem ser adicionadas aqui conforme necessário.

/**
 * Copia o conteúdo de um elemento para o clipboard.
 * Pode ser chamado de qualquer template.
 */
function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
    .then(() => showToast('Copiado para o clipboard!', 'success'))
    .catch(() => showToast('Não foi possível copiar.', 'warning'));
}

/**
 * Formata bytes para exibição legível (100KB, 2.5MB, etc.)
 */
function formatBytes(bytes) {
  if (!bytes) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit++;
  }
  return `${size.toFixed(1)} ${units[unit]}`;
}
