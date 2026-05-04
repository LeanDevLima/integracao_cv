import re
import markdown

def sanitize_and_convert_to_html(text: str) -> str:
    """
    Limpa artefatos comuns gerados por LLM e converte Markdown para HTML.
    """
    if not text:
        return ""

    # 1. Remover blocos de código markdown como ```markdown ... ```
    text = re.sub(r"```(markdown|html)?", "", text)
    text = re.sub(r"```", "", text)

    # 2. Remover marcadores do tipo [Contact][numero] ou [Email][email]
    # Padrão para pegar algo como [QualquerCoisa][OutraCoisa] que o LLM não substituiu
    text = re.sub(r"\[([^\]]+)\]\[([^\]]+)\]", r"\1", text)
    
    # 3. Remover anotações de placeholder como [Seu Nome Aqui] -> manter apenas se for útil,
    # mas o LLM geralmente gera a partir dos dados do usuário. Se ficar sujeira, removemos.
    # Exemplo: remover placeholders literais (opcional, pode ser melhor não remover para o usuário ver onde preencher)

    # Converter de Markdown para HTML
    # extensões extras: 'tables', 'fenced_code'
    html_content = markdown.markdown(text, extensions=['tables', 'fenced_code', 'nl2br'])

    return html_content
