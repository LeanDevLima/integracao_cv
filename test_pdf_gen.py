from run import create_app
from models.repositories import CurriculoGeradoRepository
from weasyprint import HTML
from utils.text_cleaner import sanitize_and_convert_to_html
from flask import render_template

app = create_app()
with app.app_context():
    curriculo = CurriculoGeradoRepository.get_by_id(1)
    if not curriculo:
        print("Curriculo not found")
    else:
        try:
            print("Curriculo id:", curriculo.id)
            html_content = sanitize_and_convert_to_html(curriculo.conteudo)
            print("Sanitized HTML length:", len(html_content))
            rendered_html = render_template('pdf/resume_template.html', content=html_content)
            print("Rendered HTML length:", len(rendered_html))
            pdf_bytes = HTML(string=rendered_html).write_pdf()
            print("PDF generated successfully, bytes length:", len(pdf_bytes))
        except Exception as e:
            import traceback
            traceback.print_exc()
