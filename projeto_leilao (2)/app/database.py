"""Inicialização do banco: cria as tabelas dos models e cadastra usuários de teste.

Cada model abre a própria conexão (ModeloBase.conectar), então aqui só
orquestramos: percorremos a lista de models e pedimos que cada um crie a sua tabela.
"""

import click
from flask.cli import with_appcontext

from app.erros import ErroIntegridade
from app.models import MODELOS
from app.models.usuario import CONTAS_TESTE, Usuario


def inicializar_banco():
    # POLIMORFISMO: o mesmo método, `criar_tabela()`, em classes diferentes.
    for modelo in MODELOS:
        modelo.criar_tabela()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Cria as tabelas e cadastra os usuários de teste."""
    inicializar_banco()
    click.echo("Tabelas criadas: " + ", ".join(modelo.TABELA for modelo in MODELOS))

    for conta in CONTAS_TESTE:
        try:
            Usuario.novo(conta["nome"], conta["email"], conta["senha"]).salvar()
            click.echo(f"  usuário criado: {conta['email']}")
        except ErroIntegridade:
            # Violou o UNIQUE do e-mail: o usuário já existe.
            click.echo(f"  já existe:      {conta['email']}")


def init_app(app):
    app.cli.add_command(init_db_command)
