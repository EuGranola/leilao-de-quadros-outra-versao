"""Configuração de logs: grava em logs/app.log (com rotação) e mostra no terminal."""

import logging
import os
from logging.handlers import RotatingFileHandler


def configurar_logs(app):
    pasta = app.config["LOG_DIR"]
    os.makedirs(pasta, exist_ok=True)

    # Todos os módulos usam logging.getLogger(__name__) ("app.controllers.auth",
    # "app.models.quadro"...), então configurar o logger "app" cobre todos.
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Evita handlers duplicados se create_app() rodar mais de uma vez.
    for antigo in list(logger.handlers):
        if getattr(antigo, "_leilao", False):
            logger.removeHandler(antigo)
            antigo.close()

    formato = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    arquivo = RotatingFileHandler(
        os.path.join(pasta, "app.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    console = logging.StreamHandler()

    for handler in (arquivo, console):
        handler.setFormatter(formato)
        handler._leilao = True
        logger.addHandler(handler)
