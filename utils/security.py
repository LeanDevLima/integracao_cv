"""
utils/security.py — Funções e classes focadas em AppSec.
"""
import re

class PromptSanitizer:
    """
    Higieniza inputs do usuário para prevenir Prompt Injection 
    e escapes não intencionais no Ollama/LLM.
    """

    @staticmethod
    def sanitize(text: str) -> str:
        """
        Limpa o texto do usuário:
        - Remove caracteres de controle ASCII que podem quebrar o parser (exceto tab, newline, return)
        - Escapa ou remove tentativas óbvias de injetar instruções de sistema como tags markdown
        """
        if not text:
            return ""
            
        # Remove control characters
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Envelopa palavras como "system", "instruction", "ignore" se estiverem em delimitadores suspeitos
        # Exemplo simples de mitigação: escapar '<' e '>' que não façam parte de tags permitidas,
        # mas como passaremos o texto dentro de <user_input>, vamos evitar que o usuário feche a tag
        cleaned = cleaned.replace('</user_input>', '< / user_input >')
        cleaned = cleaned.replace('<user_input>', '< user_input >')
        
        return cleaned

    @staticmethod
    def envelop_input(text: str) -> str:
        """Envelopa o input do usuário numa tag XML demarcada para o LLM."""
        sanitized = PromptSanitizer.sanitize(text)
        return f"<user_input>\n{sanitized}\n</user_input>"
