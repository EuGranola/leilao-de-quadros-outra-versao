"""Controller de autenticação: rotas de login e logout.

(O middleware que protege as rotas fica em app/middleware.py.)
"""

import logging
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

COOKIE_EMAIL = "email_lembrado"
COOKIE_DURACAO = 30 * 24 * 60 * 60  # 30 dias, em segundos


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("usuario_id") is not None:
            return redirect(url_for("home"))
        # COOKIE: se a pessoa pediu para lembrar o e-mail, ele volta preenchido.
        email = request.cookies.get(COOKIE_EMAIL, "")[:254]
        return render_template("login.html", email=email, lembrar=bool(email))

    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    lembrar = request.form.get("lembrar") == "on"

    usuario = Usuario.autenticar(email, senha)

    if usuario is None:
        logger.warning("Login falhou para o e-mail %r (IP %s)", email[:100], request.remote_addr)
        flash("E-mail ou senha incorretos.", "erro")
        return render_template("login.html", email=email, lembrar=lembrar), 401

    # SESSÃO: limpa antes de logar (evita fixação de sessão) e guarda só o id.
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario.id
    logger.info("Login: %s", usuario)

    resposta = redirect(destino_seguro(request.args.get("next")) or url_for("home"))

    # COOKIE: grava ou apaga o cookie do e-mail conforme a escolha da pessoa.
    if lembrar:
        resposta.set_cookie(
            COOKIE_EMAIL, usuario.email,
            max_age=COOKIE_DURACAO, httponly=True, samesite="Lax", secure=request.is_secure,
        )
    else:
        resposta.delete_cookie(COOKIE_EMAIL)
    return resposta


@auth_bp.post("/logout")
def logout():
    usuario_id = session.get("usuario_id")
    session.clear()
    logger.info("Logout (usuario=%s)", usuario_id)
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))


def destino_seguro(alvo):
    """Aceita apenas caminhos internos, para evitar open redirect."""
    if not alvo:
        return None
    analisado = urlparse(alvo)
    if analisado.netloc or analisado.scheme:
        return None
    if not alvo.startswith("/") or alvo.startswith("//") or "\\" in alvo:
        return None
    return alvo
