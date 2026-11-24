"""Upload de imagens dos quadros.

Segurança: o nome do arquivo enviado pelo usuário NUNCA é usado. Geramos um
nome aleatório e descobrimos o tipo olhando os primeiros bytes do arquivo
(a extensão pode ser falsificada, o conteúdo não).
"""

import os
import uuid

from flask import current_app


def _detectar_extensao(inicio):
    if inicio.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if inicio.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP":
        return "webp"
    return None


def _pasta_uploads():
    return os.path.join(current_app.static_folder, "uploads")


def salvar_imagem(arquivo):
    """Valida e grava a imagem. Devolve o nome salvo, ou None se nenhum arquivo foi enviado.

    Levanta ValueError (com mensagem pronta para o usuário) se o arquivo for inválido.
    """
    if arquivo is None or not arquivo.filename:
        return None

    inicio = arquivo.stream.read(12)
    arquivo.stream.seek(0)

    extensao = _detectar_extensao(inicio)
    if extensao is None:
        raise ValueError("A imagem precisa ser um arquivo JPG, PNG ou WEBP.")

    pasta = _pasta_uploads()
    os.makedirs(pasta, exist_ok=True)

    nome = f"{uuid.uuid4().hex}.{extensao}"
    arquivo.save(os.path.join(pasta, nome))
    return nome


def apagar_imagem(nome):
    """Remove uma imagem salva (usado se o INSERT falhar depois do upload)."""
    if not nome:
        return
    caminho = os.path.join(_pasta_uploads(), os.path.basename(nome))
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass
