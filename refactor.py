import re

with open('services/ai_local_service.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_funcs = False

imports_replaced = False
for i, line in enumerate(lines):
    if not imports_replaced and 'from services.ollama_client import ollama_client' in line:
        new_lines.append('from models.repositories import ProcessingLogRepository\n')
        new_lines.append('from utils.security import PromptSanitizer\n')
        new_lines.append('import logging\n')
        new_lines.append('import gc\n\n')
        new_lines.append('logger = logging.getLogger(__name__)\n')
        imports_replaced = True
        continue
    
    if 'from models.repositories import ProcessingLogRepository' in line and imports_replaced:
        continue

    if line.startswith('# ─── Funções principais ──'):
        new_lines.append(line)
        new_lines.append('\nclass AILocalService:\n')
        new_lines.append('    def __init__(self, ollama_client, log_repository=ProcessingLogRepository):\n')
        new_lines.append('        self.client = ollama_client\n')
        new_lines.append('        self.log_repo = log_repository\n\n')
        in_funcs = True
        continue
    
    if in_funcs:
        if line.startswith('def '):
            l = line.replace('def ', '    def ')
            # add self to args
            l = l.replace('(', '(self, ')
            new_lines.append(l)
        elif line.startswith('def _'):
            l = line.replace('def ', '    def ')
            l = l.replace('(', '(self, ')
            new_lines.append(l)
        elif line == '\n':
            new_lines.append(line)
        elif line.startswith('#'):
            new_lines.append('    ' + line)
        else:
            new_lines.append('    ' + line)
    else:
        new_lines.append(line)

content = "".join(new_lines)
# Do text replacements
content = content.replace('ollama_client.generate(', 'self.client.generate(')
content = content.replace('ProcessingLogRepository.create(', 'self.log_repo.create(')
content = content.replace('{job_description[:3000]}', '{PromptSanitizer.envelop_input(job_description[:3000])}')
content = content.replace('{job_description[:2500]}', '{PromptSanitizer.envelop_input(job_description[:2500])}')
content = content.replace('{job_description[:2000]}', '{PromptSanitizer.envelop_input(job_description[:2000])}')
content = content.replace('_parse_json_response(', 'self._parse_json_response(')
content = content.replace('_clamp_score(', 'self._clamp_score(')

# Add GC logic to extract_keywords
gc_add = """    elapsed_ms = int((time.time() - start) * 1000)
        del prompt
        if base_resume_text:
            del base_resume_text
        gc.collect()"""
content = content.replace('    elapsed_ms = int((time.time() - start) * 1000)', gc_add, 1)

# Add GC logic to generate_resume
gc_add2 = """    elapsed_ms = int((time.time() - start) * 1000)
        del prompt
        if base_resume_text:
            del base_resume_text
        gc.collect()"""
content = content.replace('    elapsed_ms = int((time.time() - start) * 1000)', gc_add2, 1)

# Add GC logic to generate_cover_letter
gc_add3 = """    elapsed_ms = int((time.time() - start) * 1000)
        del prompt
        if base_resume_text:
            del base_resume_text
        gc.collect()"""
content = content.replace('    elapsed_ms = int((time.time() - start) * 1000)', gc_add3, 1)


with open('services/ai_local_service.py', 'w') as f:
    f.write(content)

