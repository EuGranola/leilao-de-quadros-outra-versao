"""Middleware: código que roda ANTES e DEPOIS de toda requisição.

Antes (before_request):   1) carrega o usuário da sessão
                          2) valida o token CSRF dos POSTs
                          3) bloqueia quem não está logado
Depois (after_request):   4) registra a requisição no log e evita cache de páginas privadas

Toda rota exige login, exceto as de ROTAS_PUBLICAS. Uma rota nova criada no
futuro já nasce protegida, sem precisar de decorator.
"""

import hmac
import logging
import secrets

from flask import current_app, g, jsonify, redirect, request, session, url_for

from app.erros import ErroCSRF
from app.models.usuario import CONTAS_TESTE, Usuario

logger = logging.getLogger(__name__)

# Endpoints ("blueprint.função") que não exigem login.
ROTAS_PUBLICAS = {"auth.login", "static"}


def _token_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def init_middleware(app):
    @app.before_request
    def carregar_usuario():
        """Lê a SESSÃO e disponibiliza o usuário logado em g.usuario."""
        g.usuario = None
        usuario_id = session.get("usuario_id")
        if usuario_id is not None:
            g.usuario = Usuario.buscar_por_id(usuario_id)
            if g.usuario is None:  # sessão de um usuário que não existe mais
                logger.warning("Sessão com usuário inexistente (id=%s); sessão limpa", usuario_id)
                session.clear()

    @app.before_request
    def validar_csrf():
        """Todo POST precisa carregar o token gerado na sessão."""
        if request.method != "POST":
            return
        enviado = request.form.get("csrf_token", "")
        esperado = session.get("csrf_token", "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            logger.warning("CSRF inválido em %s (IP %s)", request.path, request.remote_addr)
            raise ErroCSRF()

    @app.before_request
    def exigir_login():
        # endpoint None = URL inexistente; deixa o Flask responder 404.
        if request.endpoint is None or request.endpoint in ROTAS_PUBLICAS:
            return
        if g.usuario is None:
            if request.path.startswith("/quadros/api"):
                return jsonify(erro="Faça login para acessar a API.", status=401), 401
            return redirect(url_for("auth.login", next=request.path))

    @app.after_request
    def registrar_e_proteger(resposta):
        if request.endpoint != "static":
            usuario = g.get("usuario")
            logger.info("%s %s -> %s (usuario=%s)", request.method, request.path,
                        resposta.status_code, usuario.id if usuario else "-")
        # Evita que o botão 'voltar' mostre páginas privadas após o logout.
        if g.get("usuario") is not None:
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    @app.context_processor
    def injetar_no_template():
        return {
            "csrf_token": _token_csrf,
            "usuario": g.get("usuario"),
            # A dica de contas de teste só aparece com debug ligado.
            "contas_teste": CONTAS_TESTE if current_app.debug else [],
        }
