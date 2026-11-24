"""Controller de quadros (C do MVC).

Aqui NÃO existe SQL. A rota recebe o formulário, instancia a classe Quadro
e chama os métodos dela. Tudo que fala com o banco está em models/quadro.py.
"""

import logging

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from app.models.quadro import Quadro
from app.paginacao import Paginacao
from app.uploads import apagar_imagem, salvar_imagem

logger = logging.getLogger(__name__)

quadros_bp = Blueprint("quadros", __name__, url_prefix="/quadros")

POR_PAGINA = 8


def _pagina_atual():
    """Monta a Paginacao a partir de ?pagina=N (valores inválidos viram 1)."""
    return Paginacao(
        pagina=request.args.get("pagina", 1, type=int),
        por_pagina=POR_PAGINA,
        total=Quadro.contar(),
    )


@quadros_bp.get("/")
def listar():
    paginacao = _pagina_atual()
    quadros = Quadro.listar(limite=paginacao.por_pagina, offset=paginacao.offset)
    return render_template("quadros/lista.html", quadros=quadros, paginacao=paginacao)


@quadros_bp.get("/api")
def api_listar():
    """A mesma listagem, em JSON (paginada)."""
    paginacao = _pagina_atual()
    quadros = Quadro.listar(limite=paginacao.por_pagina, offset=paginacao.offset)
    return jsonify(
        pagina=paginacao.pagina,
        por_pagina=paginacao.por_pagina,
        total=paginacao.total,
        total_paginas=paginacao.total_paginas,
        quadros=[_quadro_para_json(quadro) for quadro in quadros],
    )


@quadros_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "GET":
        return render_template("quadros/novo.html", valores={})

    quadro, erros = _quadro_do_formulario()

    # A imagem só é gravada em disco se o restante já estiver válido.
    if not erros:
        try:
            quadro.imagem = salvar_imagem(request.files.get("imagem"))
        except ValueError as erro:
            logger.warning("Upload recusado: %s", erro)
            erros.append(str(erro))

    if erros:
        for erro in erros:
            flash(erro, "erro")
        # Devolve o formulário preenchido, para a pessoa não digitar tudo de novo.
        return render_template("quadros/novo.html", valores=request.form.to_dict()), 400

    try:
        quadro.salvar()  # a gravação no banco acontece dentro da classe
    except Exception:
        apagar_imagem(quadro.imagem)  # não deixa arquivo órfão se o banco falhar
        raise

    logger.info("Quadro cadastrado: %s (id=%s, dono=%s)", quadro, quadro.id, quadro.dono_id)
    flash(f"“{quadro.titulo}” foi cadastrado.", "sucesso")
    return redirect(url_for("quadros.listar"))


def _quadro_do_formulario():
    """Lê o formulário, instancia o Quadro e devolve (quadro, lista_de_erros)."""
    erros = []

    try:
        preco = Quadro.reais_para_centavos(request.form.get("preco", ""))
    except ValueError as erro:
        preco = None
        erros.append(str(erro))

    try:
        ano = Quadro.texto_para_ano(request.form.get("ano", ""))
    except ValueError as erro:
        ano = None
        erros.append(str(erro))

    quadro = Quadro(
        titulo=request.form.get("titulo", ""),
        artista=request.form.get("artista", ""),
        ano=ano,
        tecnica=request.form.get("tecnica", ""),
        descricao=request.form.get("descricao", ""),
        preco_inicial=preco,
        dono_id=g.usuario.id,  # o dono é sempre quem está logado
    )
    erros += quadro.validar()
    return quadro, erros


def _quadro_para_json(quadro):
    dados = quadro.para_dict()
    dados["imagem_url"] = (
        url_for("static", filename=f"uploads/{quadro.imagem}") if quadro.imagem else None
    )
    return dados
