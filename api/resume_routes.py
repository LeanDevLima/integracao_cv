import os
import io
from flask import send_file, render_template
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from weasyprint import HTML

from models.repositories import CurriculoGeradoRepository
from utils.text_cleaner import sanitize_and_convert_to_html

resume_ns = Namespace('resumes', description='Gestão e exportação de Currículos', path='/resumes')

@resume_ns.route('/<int:resume_id>/download')
class ResumeDownload(Resource):
    @jwt_required()
    @resume_ns.response(200, 'PDF do currículo gerado')
    @resume_ns.response(404, 'Currículo não encontrado')
    def get(self, resume_id):
        """
        Gera e faz o download do currículo em formato PDF.
        """
        user_id = get_jwt_identity()
        curriculo = CurriculoGeradoRepository.get_by_id(resume_id)

        if not curriculo or curriculo.usuario_id != int(user_id):
            return {'error': 'Currículo não encontrado.'}, 404

        # Limpar e converter conteúdo Markdown para HTML
        html_content = sanitize_and_convert_to_html(curriculo.conteudo)

        # Renderizar no template Jinja2 focado em impressão
        rendered_html = render_template('pdf/resume_template.html', content=html_content)

        # Gerar o PDF em memória usando WeasyPrint
        pdf_bytes = HTML(string=rendered_html).write_pdf()

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Curriculo_Vaga_{curriculo.vaga_id}.pdf'
        )

@resume_ns.route('/<int:resume_id>')
class ResumeDelete(Resource):
    @jwt_required()
    @resume_ns.response(200, 'Currículo gerado excluído com sucesso')
    @resume_ns.response(404, 'Currículo não encontrado')
    def delete(self, resume_id):
        """Exclui um currículo gerado."""
        user_id = get_jwt_identity()
        curriculo = CurriculoGeradoRepository.get_by_id(resume_id)
        
        if not curriculo or curriculo.usuario_id != int(user_id):
            return {'error': 'Currículo não encontrado.'}, 404
            
        CurriculoGeradoRepository.delete(curriculo)
        return {'message': 'Currículo excluído com sucesso.'}, 200
