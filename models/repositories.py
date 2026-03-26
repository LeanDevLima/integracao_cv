"""
models/repositories.py — Camada de acesso a dados (Repository Pattern).
Cada repositório encapsula as operações de CRUD para sua entidade,
mantendo a lógica de negócio separada das rotas.
"""
from extensions import db
from .models import Usuario, Vaga, CurriculoGerado, CoverLetterGerada, Keyword, ProcessingLog
import json


# ─── UsuarioRepository ───────────────────────────────────────────────────────
class UsuarioRepository:

    @staticmethod
    def create(nome: str, email: str, senha_hash: str, **kwargs) -> Usuario:
        usuario = Usuario(nome=nome, email=email, senha_hash=senha_hash, **kwargs)
        db.session.add(usuario)
        db.session.commit()
        return usuario

    @staticmethod
    def get_by_id(user_id: int) -> Usuario | None:
        return db.session.get(Usuario, user_id)

    @staticmethod
    def get_by_email(email: str) -> Usuario | None:
        return Usuario.query.filter_by(email=email).first()

    @staticmethod
    def update(usuario: Usuario, **kwargs) -> Usuario:
        for key, value in kwargs.items():
            if hasattr(usuario, key):
                setattr(usuario, key, value)
        db.session.commit()
        return usuario

    @staticmethod
    def delete(usuario: Usuario) -> None:
        db.session.delete(usuario)
        db.session.commit()

    @staticmethod
    def email_exists(email: str) -> bool:
        return Usuario.query.filter_by(email=email).count() > 0


# ─── VagaRepository ──────────────────────────────────────────────────────────
class VagaRepository:

    @staticmethod
    def create(usuario_id: int, titulo: str, descricao_completa: str, **kwargs) -> Vaga:
        vaga = Vaga(
            usuario_id=usuario_id,
            titulo=titulo,
            descricao_completa=descricao_completa,
            **kwargs
        )
        db.session.add(vaga)
        db.session.commit()
        return vaga

    @staticmethod
    def get_by_id(vaga_id: int) -> Vaga | None:
        return db.session.get(Vaga, vaga_id)

    @staticmethod
    def list_by_user(usuario_id: int, page: int = 1, per_page: int = 20):
        return (Vaga.query
                .filter_by(usuario_id=usuario_id)
                .order_by(Vaga.created_at.desc())
                .paginate(page=page, per_page=per_page, error_out=False))

    @staticmethod
    def update(vaga: Vaga, **kwargs) -> Vaga:
        for key, value in kwargs.items():
            if hasattr(vaga, key):
                setattr(vaga, key, value)
        db.session.commit()
        return vaga

    @staticmethod
    def update_analise(vaga: Vaga, match_score: float, keywords: list, analise_resumo: str) -> Vaga:
        """Atualiza os campos de análise de IA da vaga."""
        vaga.match_score = match_score
        vaga.palavras_chave_extraidas = json.dumps(keywords, ensure_ascii=False)
        vaga.analise_resumo = analise_resumo
        vaga.status = 'analisado'
        db.session.commit()
        return vaga

    @staticmethod
    def delete(vaga: Vaga) -> None:
        db.session.delete(vaga)
        db.session.commit()


# ─── CurriculoGeradoRepository ───────────────────────────────────────────────
class CurriculoGeradoRepository:

    @staticmethod
    def create(vaga_id: int, usuario_id: int, conteudo: str, **kwargs) -> CurriculoGerado:
        curriculo = CurriculoGerado(
            vaga_id=vaga_id,
            usuario_id=usuario_id,
            conteudo=conteudo,
            **kwargs
        )
        db.session.add(curriculo)
        db.session.commit()
        return curriculo

    @staticmethod
    def get_by_id(curriculo_id: int) -> CurriculoGerado | None:
        return db.session.get(CurriculoGerado, curriculo_id)

    @staticmethod
    def list_by_user(usuario_id: int) -> list[CurriculoGerado]:
        return (CurriculoGerado.query
                .filter_by(usuario_id=usuario_id)
                .order_by(CurriculoGerado.created_at.desc())
                .all())

    @staticmethod
    def list_by_vaga(vaga_id: int) -> list[CurriculoGerado]:
        return (CurriculoGerado.query
                .filter_by(vaga_id=vaga_id)
                .order_by(CurriculoGerado.created_at.desc())
                .all())

    @staticmethod
    def delete(curriculo: CurriculoGerado) -> None:
        db.session.delete(curriculo)
        db.session.commit()


# ─── CoverLetterGeradaRepository ─────────────────────────────────────────────
class CoverLetterGeradaRepository:

    @staticmethod
    def create(vaga_id: int, usuario_id: int, conteudo: str, **kwargs) -> CoverLetterGerada:
        cover = CoverLetterGerada(
            vaga_id=vaga_id,
            usuario_id=usuario_id,
            conteudo=conteudo,
            **kwargs
        )
        db.session.add(cover)
        db.session.commit()
        return cover

    @staticmethod
    def get_by_id(cover_id: int) -> CoverLetterGerada | None:
        return db.session.get(CoverLetterGerada, cover_id)

    @staticmethod
    def list_by_user(usuario_id: int) -> list[CoverLetterGerada]:
        return (CoverLetterGerada.query
                .filter_by(usuario_id=usuario_id)
                .order_by(CoverLetterGerada.created_at.desc())
                .all())

    @staticmethod
    def list_by_vaga(vaga_id: int) -> list[CoverLetterGerada]:
        return (CoverLetterGerada.query
                .filter_by(vaga_id=vaga_id)
                .order_by(CoverLetterGerada.created_at.desc())
                .all())

    @staticmethod
    def delete(cover: CoverLetterGerada) -> None:
        db.session.delete(cover)
        db.session.commit()


# ─── KeywordRepository ───────────────────────────────────────────────────────
class KeywordRepository:

    @staticmethod
    def get_or_create(texto: str) -> Keyword:
        """Busca keyword existente ou cria uma nova."""
        kw = Keyword.query.filter_by(texto=texto.lower().strip()).first()
        if not kw:
            kw = Keyword(texto=texto.lower().strip())
            db.session.add(kw)
            db.session.flush()  # obtém o id sem commit
        return kw

    @staticmethod
    def bulk_get_or_create(textos: list[str]) -> list[Keyword]:
        """Processa uma lista de keywords de uma vez."""
        keywords = []
        for texto in textos:
            if texto and texto.strip():
                kw = KeywordRepository.get_or_create(texto)
                keywords.append(kw)
        db.session.commit()
        return keywords


# ─── ProcessingLogRepository ─────────────────────────────────────────────────
class ProcessingLogRepository:

    @staticmethod
    def create(usuario_id: int, tipo_operacao: str, modelo: str,
               tokens_usados: int = 0, tempo_ms: int = 0,
               sucesso: bool = True, erro_msg: str = None) -> ProcessingLog:
        log = ProcessingLog(
            usuario_id=usuario_id,
            tipo_operacao=tipo_operacao,
            modelo=modelo,
            tokens_usados=tokens_usados,
            tempo_ms=tempo_ms,
            sucesso=sucesso,
            erro_msg=erro_msg
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def list_by_user(usuario_id: int, limit: int = 50) -> list[ProcessingLog]:
        return (ProcessingLog.query
                .filter_by(usuario_id=usuario_id)
                .order_by(ProcessingLog.created_at.desc())
                .limit(limit)
                .all())
