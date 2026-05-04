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
    preferencia_modelo_ia = db.Column(db.String(100), default='llama3')
    created_at           = db.Column(db.DateTime,    default=datetime.utcnow)

    # Relacionamentos
    base_resumes      = db.relationship('BaseResume',       backref='usuario', lazy=True, cascade='all, delete-orphan')
    vagas             = db.relationship('Vaga',             backref='usuario', lazy=True, cascade='all, delete-orphan')
    curriculos_gerados = db.relationship('CurriculoGerado', backref='usuario', lazy=True)
    cover_letters     = db.relationship('CoverLetterGerada', backref='usuario', lazy=True)
    processing_logs   = db.relationship('ProcessingLog',    backref='usuario', lazy=True)

    def to_dict(self):
        active_resume = next((r for r in self.base_resumes if r.is_active), None)
        return {
            'id':                   self.id,
            'nome':                 self.nome,
            'email':                self.email,
            'preferencia_modelo_ia': self.preferencia_modelo_ia,
            'tem_curriculo':        bool(active_resume),
            'created_at':           self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Usuario {self.email}>'


# ─── BaseResume ──────────────────────────────────────────────────────────────
class BaseResume(db.Model):
    __tablename__ = 'base_resumes'

    id             = db.Column(db.Integer,    primary_key=True)
    usuario_id     = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=False)
    file_name      = db.Column(db.String(255), nullable=False)
    original_file_name = db.Column(db.String(255))
    file_path      = db.Column(db.String(500), nullable=False)
    conteudo_texto = db.Column(db.Text,       nullable=False)
    is_active      = db.Column(db.Boolean,    default=False)
    upload_date    = db.Column(db.DateTime,   default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                 self.id,
            'usuario_id':         self.usuario_id,
            'file_name':          self.file_name,
            'original_file_name': self.original_file_name,
            'is_active':          self.is_active,
            'upload_date':        self.upload_date.isoformat() if self.upload_date else None,
        }

    def __repr__(self):
        return f'<BaseResume {self.file_name}>'


# ─── Vaga ────────────────────────────────────────────────────────────────────
class Vaga(db.Model):
    __tablename__ = 'vagas'

    id                      = db.Column(db.Integer,    primary_key=True)
    usuario_id              = db.Column(db.Integer,    db.ForeignKey('usuarios.id'), nullable=False)
    titulo                  = db.Column(db.String(300), nullable=False)
    empresa                 = db.Column(db.String(300))
    descricao_completa      = db.Column(db.Text,       nullable=False)
    pais                    = db.Column(db.String(100))
    idioma_geracao          = db.Column(db.String(50), default='pt-BR')
    curriculo_base_utilizado_nome = db.Column(db.String(255))
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
            'pais':                    self.pais,
            'idioma_geracao':          self.idioma_geracao,
            'curriculo_base_utilizado_nome': self.curriculo_base_utilizado_nome,
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
