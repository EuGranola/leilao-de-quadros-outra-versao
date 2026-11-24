"""ModeloBase: classe ABSTRATA da qual todo model herda.

ABSTRAÇÃO:    define O QUE todo model precisa saber fazer (os métodos
              @abstractmethod), sem dizer COMO. Não dá para criar um
              ModeloBase() direto: só as classes filhas.
HERANÇA:      Usuario e Quadro herdam daqui o `conectar()` e os helpers de SQL,
              em vez de repetir esse código nas duas.
POLIMORFISMO: cada filha implementa os métodos abstratos do jeito dela, e o
              resto do sistema chama `modelo.criar_tabela()`, `obj.validar()`,
              `obj.para_dict()` sem precisar saber se é um Usuario ou um Quadro.
"""

import logging
import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing

from flask import current_app

from app.erros import ErroBancoDados, ErroIntegridade

logger = logging.getLogger(__name__)


class ModeloBase(ABC):
    TABELA = ""  # cada filha informa o nome da sua tabela

    # ----- Parte concreta (herdada por todos) -----

    @staticmethod
    def conectar():
        """Abre uma conexão com o arquivo .db. Quem abre é quem fecha."""
        conexao = sqlite3.connect(current_app.config["DATABASE"])
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    @classmethod
    def _executar(cls, sql, parametros=()):
        """Executa um comando de escrita (CREATE, INSERT...). Devolve o lastrowid.

        O `_` no começo indica método protegido: é para uso das classes filhas.
        """
        try:
            with closing(cls.conectar()) as conexao:
                with conexao:  # transação: commit se deu certo, rollback se deu erro
                    return conexao.execute(sql, parametros).lastrowid
        except sqlite3.IntegrityError as erro:
            logger.warning("Violação de integridade em %s: %s", cls.TABELA, erro)
            raise ErroIntegridade() from erro
        except sqlite3.Error as erro:
            logger.exception("Falha de escrita no banco (%s)", cls.TABELA)
            raise ErroBancoDados() from erro

    @classmethod
    def _consultar(cls, sql, parametros=()):
        """Executa um SELECT e devolve todas as linhas (lista de sqlite3.Row)."""
        try:
            with closing(cls.conectar()) as conexao:
                return conexao.execute(sql, parametros).fetchall()
        except sqlite3.Error as erro:
            logger.exception("Falha de leitura no banco (%s)", cls.TABELA)
            raise ErroBancoDados() from erro

    def __repr__(self):
        return f"<{type(self).__name__} id={getattr(self, 'id', None)}>"

    # ----- Parte abstrata (cada filha É OBRIGADA a implementar) -----

    @classmethod
    @abstractmethod
    def criar_tabela(cls):
        """CREATE TABLE IF NOT EXISTS da entidade."""

    @classmethod
    @abstractmethod
    def _de_linha(cls, linha):
        """Transforma uma linha do banco (sqlite3.Row) em objeto."""

    @abstractmethod
    def salvar(self):
        """INSERT do objeto no banco."""

    @abstractmethod
    def validar(self):
        """Devolve a lista de mensagens de erro (vazia = tudo certo)."""

    @abstractmethod
    def para_dict(self):
        """Representação em dicionário, pronta para virar JSON."""

    @abstractmethod
    def __str__(self):
        """Texto curto para mostrar em logs e mensagens."""
