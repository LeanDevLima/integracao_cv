import re

with open('services/ai_local_service.py', 'r') as f:
    content = f.read()

# Substituir imports
content = content.replace("from models.repositories import ProcessingLogRepository", "from models.repositories import ProcessingLogRepository\nfrom utils.security import PromptSanitizer\nimport logging\nimport gc\n\nlogger = logging.getLogger(__name__)")

# Procurar as def e substituir por classe
new_class = """class AILocalService:
    def __init__(self, ollama_client, log_repository=ProcessingLogRepository):
        self.client = ollama_client
        self.log_repo = log_repository

    def extract_keywords(self, job_description: str, base_resume_text: str,
                         model: str, usuario_id: Optional[int] = None) -> dict:"""

content = content.replace("def extract_keywords(job_description: str, base_resume_text: str,\n                     model: str, usuario_id: Optional[int] = None) -> dict:", new_class)

content = content.replace("def generate_resume(", "def generate_resume(self, ")
content = content.replace("def generate_cover_letter(", "def generate_cover_letter(self, ")
content = content.replace("def _parse_json_response(", "def _parse_json_response(self, ")
content = content.replace("def _clamp_score(", "def _clamp_score(self, ")

# Substituir ProcessingLogRepository.create por self.log_repo.create
content = content.replace("ProcessingLogRepository.create(", "self.log_repo.create(")

# Substituir ollama_client por self.client
content = content.replace("ollama_client.generate(", "self.client.generate(")

# Indentar o corpo das funções
lines = content.split('\n')
new_lines = []
in_class = False
for line in lines:
    if line.startswith("class AILocalService:"):
        in_class = True
        new_lines.append(line)
    elif in_class and line and not line.startswith(" ") and not line.startswith("def") and not line.startswith("#"):
        # Fim da indentação (não deveria ocorrer se tudo for def)
        new_lines.append("    " + line)
    elif in_class and line.startswith("def "):
        new_lines.append("    " + line)
    elif in_class and line.startswith(" "):
        new_lines.append("    " + line)
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

# Envelopar inputs com PromptSanitizer
content = content.replace("{job_description[:3000]}", "{PromptSanitizer.envelop_input(job_description[:3000])}")
content = content.replace("{job_description[:2500]}", "{PromptSanitizer.envelop_input(job_description[:2500])}")
content = content.replace("{job_description[:2000]}", "{PromptSanitizer.envelop_input(job_description[:2000])}")

# Adicionar GC (garbage collection)
gc_code = """    del prompt
        if base_resume_text:
            del base_resume_text
        gc.collect()"""

# Inserir o GC code após pegar result
content = content.replace("elapsed_ms = int((time.time() - start) * 1000)", f"elapsed_ms = int((time.time() - start) * 1000)\n    {gc_code}")

# _parse_json_response self fix
content = content.replace("_parse_json_response(", "self._parse_json_response(")
content = content.replace("_clamp_score(", "self._clamp_score(")

with open('services/ai_local_service.py', 'w') as f:
    f.write(content)

