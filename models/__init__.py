"""
models/__init__.py — Expõe os modelos para importação conveniente.
"""
from .models import (
    db, Usuario, Vaga, CurriculoGerado,
    CoverLetterGerada, Keyword, ProcessingLog, vaga_keywords
)

__all__ = [
    'db', 'Usuario', 'Vaga', 'CurriculoGerado',
    'CoverLetterGerada', 'Keyword', 'ProcessingLog', 'vaga_keywords'
]
