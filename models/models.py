"""
models/models.py — Entidades SQLAlchemy do Job Assistant IA.

Relacionamentos implementados:
  - Usuario 1→N Vaga (cascade delete)
  - Vaga N→M Keyword (via tabela associativa vaga_keywords)
  - Vaga 1→N CurriculoGerado (cascade delete)
  - Vaga 1→N CoverLetterGerada (cascade delete)
  - Usuario 1→N ProcessingLog (telemetria do Ollama)
"""
from datetime import datetime
from extensions import db

# ─── Tabela associativa M2M: Vaga ↔ Keyword ─────────────────────────────────
vaga_keywords = db.Table(
    'vaga_keywords',
    db.Column('vaga_id',    db.Integer, db.ForeignKey('vagas.id'),    primary_key=True),
    db.Column('keyword_id', db.Integer, db.ForeignKey('keywords.id'), primary_key=True)
)


# ─── Usuario ─────────────────────────────────────────────────────────────────
class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id                   = db.Column(db.Integer,     primary_key=True)
    nome                 = db.Column(db.String(200),  nullable=False)
    email                = db.Column(db.String(200),  unique=True, nullable=False, index=True)
    senha_hash           = db.Column(db.String(255),  nullable=False)
    curriculo_base_path  = db.Column(db.String(500))   # caminho do arquivo enviado
    curriculo_base_texto = db.Column(db.Text)          # texto extraído do PDF/DOCX
    preferencia_modelo_ia = db.Column(db.String(100), default='llama3')
    created_at           = db.Column(db.DateTime,    default=datetime.utcnow)

    # Relacionamentos
    vagas             = db.relationship('Vaga',             backref='usuario', lazy=True, cascade='all, delete-orphan')
    curriculos_gerados = db.relationship('CurriculoGerado', backref='usuario', lazy=True)
    cover_letters     = db.relationship('CoverLetterGerada', backref='usuario', lazy=True)
    processing_logs   = db.relationship('ProcessingLog',    backref='usuario', lazy=True)

    def to_dict(self):
        return {
            'id':                   self.id,
            'nome':                 self.nome,
            'email':                self.email,
            'preferencia_modelo_ia': self.preferencia_modelo_ia,
            'tem_curriculo':        bool(self.curriculo_base_path),
            'created_at':           self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Usuario {self.email}>'


# ─── Vaga ────────────────────────────────────────────────────────────────────
class Vaga(db.Model):
    __tablename__ = 'vagas'

    id                      = db.Column(db.Integer,    primary_key=True)
    usuario_id              = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=False)
    titulo                  = db.Column(db.String(300), nullable=False)
    empresa                 = db.Column(db.String(300))
    descricao_completa      = db.Column(db.Text,       nullable=False)
    palavras_chave_extraidas = db.Column(db.Text)      # JSON string com lista de keywords
    match_score             = db.Column(db.Float,      default=0.0)
    status                  = db.Column(db.String(50), default='pendente')  # pendente | analisado | gerado
    analise_resumo          = db.Column(db.Text)       # análise textual do match
    created_at              = db.Column(db.DateTime,   default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    keywords          = db.relationship('Keyword',          secondary=vaga_keywords, lazy='subquery',
                                        backref=db.backref('vagas', lazy=True))
    curriculos_gerados = db.relationship('CurriculoGerado', backref='vaga', lazy=True, cascade='all, delete-orphan')
    cover_letters     = db.relationship('CoverLetterGerada', backref='vaga', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        import json
        kw_list = []
        if self.palavras_chave_extraidas:
            try:
                kw_list = json.loads(self.palavras_chave_extraidas)
            except (json.JSONDecodeError, TypeError):
                kw_list = []
        return {
            'id':                      self.id,
            'usuario_id':              self.usuario_id,
            'titulo':                  self.titulo,
            'empresa':                 self.empresa,
            'descricao_completa':      self.descricao_completa,
            'palavras_chave_extraidas': kw_list,
            'match_score':             self.match_score,
            'status':                  self.status,
            'analise_resumo':          self.analise_resumo,
            'created_at':              self.created_at.isoformat() if self.created_at else None,
            'num_curriculos':          len(self.curriculos_gerados),
            'num_cover_letters':       len(self.cover_letters),
        }

    def __repr__(self):
        return f'<Vaga {self.titulo} @ {self.empresa}>'


# ─── CurriculoGerado ─────────────────────────────────────────────────────────
class CurriculoGerado(db.Model):
    __tablename__ = 'curriculos_gerados'

    id                 = db.Column(db.Integer,    primary_key=True)
    vaga_id            = db.Column(db.Integer,    db.ForeignKey('vagas.id'),    nullable=False)
    usuario_id         = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=False)
    conteudo           = db.Column(db.Text,       nullable=False)
    modelo_ia_utilizado = db.Column(db.String(100))
    tempo_inferencia   = db.Column(db.Float)       # segundos
    tokens             = db.Column(db.Integer)
    created_at         = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                 self.id,
            'vaga_id':            self.vaga_id,
            'usuario_id':         self.usuario_id,
            'conteudo':           self.conteudo,
            'modelo_ia_utilizado': self.modelo_ia_utilizado,
            'tempo_inferencia':   self.tempo_inferencia,
            'tokens':             self.tokens,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<CurriculoGerado id={self.id} vaga={self.vaga_id}>'


# ─── CoverLetterGerada ───────────────────────────────────────────────────────
class CoverLetterGerada(db.Model):
    __tablename__ = 'cover_letters_geradas'

    id                 = db.Column(db.Integer,    primary_key=True)
    vaga_id            = db.Column(db.Integer,    db.ForeignKey('vagas.id'),    nullable=False)
    usuario_id         = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=False)
    conteudo           = db.Column(db.Text,       nullable=False)
    modelo_ia_utilizado = db.Column(db.String(100))
    tempo_inferencia   = db.Column(db.Float)       # segundos
    tokens             = db.Column(db.Integer)
    created_at         = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                 self.id,
            'vaga_id':            self.vaga_id,
            'usuario_id':         self.usuario_id,
            'conteudo':           self.conteudo,
            'modelo_ia_utilizado': self.modelo_ia_utilizado,
            'tempo_inferencia':   self.tempo_inferencia,
            'tokens':             self.tokens,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<CoverLetterGerada id={self.id} vaga={self.vaga_id}>'


# ─── Keyword ─────────────────────────────────────────────────────────────────
class Keyword(db.Model):
    __tablename__ = 'keywords'

    id    = db.Column(db.Integer,    primary_key=True)
    texto = db.Column(db.String(200), unique=True, nullable=False, index=True)

    def to_dict(self):
        return {'id': self.id, 'texto': self.texto}

    def __repr__(self):
        return f'<Keyword {self.texto}>'


# ─── ProcessingLog ───────────────────────────────────────────────────────────
class ProcessingLog(db.Model):
    """Telemetria das operações de IA local com Ollama."""
    __tablename__ = 'processing_logs'

    id             = db.Column(db.Integer,    primary_key=True)
    usuario_id     = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=False)
    tipo_operacao  = db.Column(db.String(100))  # 'keyword_extraction' | 'resume_generation' | 'cover_letter'
    modelo         = db.Column(db.String(100))
    tokens_usados  = db.Column(db.Integer)
    tempo_ms       = db.Column(db.Integer)
    sucesso        = db.Column(db.Boolean,    default=True)
    erro_msg       = db.Column(db.Text)
    created_at     = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':            self.id,
            'usuario_id':    self.usuario_id,
            'tipo_operacao': self.tipo_operacao,
            'modelo':        self.modelo,
            'tokens_usados': self.tokens_usados,
            'tempo_ms':      self.tempo_ms,
            'sucesso':       self.sucesso,
            'erro_msg':      self.erro_msg,
            'created_at':    self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ProcessingLog {self.tipo_operacao} sucesso={self.sucesso}>'
