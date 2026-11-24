"""Tratamento de erros.

1) Exceções próprias, com HERANÇA:  ErroDaAplicacao -> ErroBancoDados -> ErroIntegridade
2) Handlers: transformam qualquer erro numa página amigável (ou num JSON,
   se a requisição for para a API), e registram o problema no log.
"""

import logging

from flask import flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ErroDaAplicacao(Exception):
    """Classe-mãe de todos os erros previstos pelo sistema."""

    status = 500
    mensagem_usuario = "Algo deu errado do nosso lado. Tente novamente em instantes."

    def __init__(self, mensagem_usuario=None):
        if mensagem_usuario:
            self.mensagem_usuario = mensagem_usuario
        super().__init__(self.mensagem_usuario)


class ErroBancoDados(ErroDaAplicacao):
    mensagem_usuario = "Não foi possível acessar o banco de dados agora. Tente novamente em instantes."


class ErroIntegridade(ErroBancoDados):
    """Violou uma regra do banco (UNIQUE, CHECK, chave estrangeira...)."""

    status = 409
    mensagem_usuario = "Esse registro conflita com outro que já existe."


class ErroCSRF(ErroDaAplicacao):
    status = 400
    mensagem_usuario = "O formulário expirou. Recarregue a página e tente de novo."


TITULOS = {
    400: "Requisição inválida",
    401: "Login necessário",
    403: "Acesso negado",
    404: "Página não encontrada",
    405: "Método não permitido",
    409: "Registro em conflito",
    413: "Arquivo grande demais",
    500: "Algo deu errado",
}

MENSAGENS = {
    400: "Não foi possível entender a requisição.",
    403: "Você não tem permissão para acessar isso.",
    404: "O endereço que você abriu não existe ou foi removido.",
    405: "Essa ação não é permitida neste endereço.",
    500: "Algo deu errado do nosso lado. Tente novamente em instantes.",
}


def _requisicao_de_api():
    return request.path.startswith("/quadros/api")


def _responder(status, mensagem):
    if _requisicao_de_api():
        return jsonify(erro=mensagem, status=status), status
    return render_template(
        "erros/erro.html",
        status=status,
        titulo=TITULOS.get(status, "Ops"),
        mensagem=mensagem,
    ), status


def registrar_handlers(app):
    @app.errorhandler(ErroDaAplicacao)
    def erro_da_aplicacao(erro):
        # Vale para ErroBancoDados, ErroIntegridade, ErroCSRF... (herança).
        nivel = logging.ERROR if erro.status >= 500 else logging.WARNING
        logger.log(nivel, "%s em %s %s", type(erro).__name__, request.method, request.path)
        return _responder(erro.status, erro.mensagem_usuario)

    @app.errorhandler(413)
    def arquivo_grande(erro):
        logger.warning("Upload acima do limite em %s", request.path)
        flash("A imagem é grande demais. O limite é 5 MB.", "erro")
        return redirect(url_for("quadros.novo"))

    @app.errorhandler(500)
    def erro_interno(erro):
        # Erro que ninguém previu: guarda o traceback completo no log,
        # mas mostra só uma mensagem genérica para a pessoa.
        original = getattr(erro, "original_exception", None) or erro
        logger.error("Erro inesperado em %s %s", request.method, request.path, exc_info=original)
        return _responder(500, MENSAGENS[500])

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        # 404, 405 etc. (o 413 e o 500 têm handler próprio acima)
        return _responder(erro.code, MENSAGENS.get(erro.code, "Não foi possível concluir a requisição."))
