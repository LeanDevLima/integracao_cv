"""
wsgi.py — Ponto de entrada para servidores WSGI em produção (ex: Gunicorn).

Uso com Gunicorn (Linux/Produção):
    gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 wsgi:app

O timeout de 120 segundos é crítico porque operações do Ollama
(especialmente a primeira geração com um modelo pesado) podem 
demorar consideravelmente.
"""

from run import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
