import os
from datetime import timedelta

from flask import Flask, redirect, url_for

from app import database
from app.controllers.auth import auth_bp
from app.controllers.quadros import quadros_bp
from app.erros import registrar_handlers
from app.logs import configurar_logs
from app.middleware import init_middleware


def create_app(config=None):
    # Os templates Jinja2 ficam em app/views (em vez do padrão "templates").
    app = Flask(__name__, template_folder="views", static_folder="static")

    app.config.update(
        # Em produção, defina a variável de ambiente SECRET_KEY com um valor longo e aleatório.
        SECRET_KEY=os.environ.get("SECRET_KEY", "chave-apenas-para-desenvolvimento"),
        # Cookie de sessão: expira em 2 h, inacessível por JavaScript.
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Ative quando servir por HTTPS:
        # SESSION_COOKIE_SECURE=True,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # limite de upload: 5 MB
        # O arquivo do banco fica na pasta "instance/", na raiz do projeto.
        DATABASE=os.path.join(app.instance_path, "leilao.db"),
        # Os logs ficam na pasta "logs/", na raiz do projeto.
        LOG_DIR=os.path.join(os.path.dirname(app.root_path), "logs"),
    )
    if config:  # permite sobrescrever (útil em testes)
        app.config.update(config)

    os.makedirs(app.instance_path, exist_ok=True)
    app.json.ensure_ascii = False  # JSON legível: "Óleo", e não "\u00d3leo"

    configurar_logs(app)
    init_middleware(app)       # sessão, CSRF, proteção de rotas, log de requisições
    registrar_handlers(app)    # páginas/JSON de erro
    database.init_app(app)     # comando: flask --app run init-db

    app.register_blueprint(auth_bp)
    app.register_blueprint(quadros_bp)

    @app.route("/")
    def home():
        # A página inicial do leilão é a própria listagem de obras.
        return redirect(url_for("quadros.listar"))

    # Garante que as tabelas existam ao iniciar (CREATE TABLE IF NOT EXISTS
    # não apaga nada). Os usuários de teste continuam vindo do `init-db`.
    with app.app_context():
        database.inicializar_banco()

    app.logger.info("Aplicação iniciada (banco: %s)", app.config["DATABASE"])
    return app
