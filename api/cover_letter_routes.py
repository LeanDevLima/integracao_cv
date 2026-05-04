import io
from flask import send_file, render_template
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from weasyprint import HTML

from models.repositories import CoverLetterGeradaRepository
from utils.text_cleaner import sanitize_and_convert_to_html

cover_letter_ns = Namespace('cover-letters', description='Gestão e exportação de Cover Letters', path='/cover-letters')

@cover_letter_ns.route('/<int:cover_id>/download')
class CoverLetterDownload(Resource):
    @jwt_required()
    @cover_letter_ns.response(200, 'PDF da cover letter gerado')
    @cover_letter_ns.response(404, 'Cover letter não encontrada')
    def get(self, cover_id):
        """
        Gera e faz o download da Cover Letter em formato PDF.
        """
        user_id = get_jwt_identity()
        cover = CoverLetterGeradaRepository.get_by_id(cover_id)

        if not cover or cover.usuario_id != int(user_id):
            return {'error': 'Cover letter não encontrada.'}, 404

        # Limpar e converter conteúdo Markdown para HTML
        html_content = sanitize_and_convert_to_html(cover.conteudo)

        # Renderizar no template Jinja2 focado em impressão
        rendered_html = render_template('pdf/cover_letter_template.html', content=html_content)

        # Gerar o PDF em memória usando WeasyPrint
        pdf_bytes = HTML(string=rendered_html).write_pdf()

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Cover_Letter_Vaga_{cover.vaga_id}.pdf'
        )

@cover_letter_ns.route('/<int:cover_id>')
class CoverLetterDelete(Resource):
    @jwt_required()
    @cover_letter_ns.response(200, 'Cover letter excluída com sucesso')
    @cover_letter_ns.response(404, 'Cover letter não encontrada')
    def delete(self, cover_id):
        """Exclui uma cover letter gerada."""
        user_id = get_jwt_identity()
        cover = CoverLetterGeradaRepository.get_by_id(cover_id)
        
        if not cover or cover.usuario_id != int(user_id):
            return {'error': 'Cover letter não encontrada.'}, 404
            
        CoverLetterGeradaRepository.delete(cover)
        return {'message': 'Cover letter excluída com sucesso.'}, 200
