"""
RASTRO — Flask + HTML + CSS + JS puro, com login real e dados em MySQL.

Sidebar no desktop, bottom-nav no celular, cards em glassmorphism,
TALK → barreira → 1% → WORLD → PERFIL e SECRET.

Este arquivo só monta o app: configuração, banco, blueprints e comandos de
terminal. As rotas ficam em routes/ (uma por área), as regras de negócio em
services/, as tabelas em models.py e o conteúdo fixo em data.py.

    python app.py            sobe o servidor em http://localhost:5000
    flask --app app init-db  cria as tabelas
"""

from flask import Flask, session

import cli
import routes
from config import Config
from models import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.secret_key = app.config["SECRET_KEY"]

    db.init_app(app)
    routes.register(app)
    cli.register(app)

    @app.context_processor
    def inject_just_registered():
        # consome a flag uma única vez: some da sessão assim que a primeira
        # página é renderizada depois do cadastro (ver routes/auth.py),
        # então o modal "Conta criada!" nunca reaparece num refresh.
        return {"just_registered": session.pop("just_registered", False)}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
