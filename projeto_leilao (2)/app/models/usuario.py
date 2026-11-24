"""Model Usuario (herda de ModeloBase)."""

import re

from werkzeug.security import check_password_hash, generate_password_hash

from app.models.base import ModeloBase

# Dados usados só pelo comando `init-db` (e pela dica na tela de login em debug).
CONTAS_TESTE = [
    {"nome": "Ana Souza", "email": "ana@leilao.test", "senha": "ana123"},
    {"nome": "Bruno Lima", "email": "bruno@leilao.test", "senha": "bruno123"},
    {"nome": "Carla Mendes", "email": "carla@leilao.test", "senha": "carla123"},
]

# Usado quando o e-mail não existe, para o tempo de resposta ser parecido
# nos dois casos (e-mail inexistente x senha errada).
_HASH_FALSO = generate_password_hash("senha-falsa")

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Usuario(ModeloBase):
    TABELA = "usuarios"

    def __init__(self, nome, email, senha_hash=None, id=None, criado_em=None):
        self.id = id
        self.nome = (nome or "").strip()
        self.email = (email or "").strip().lower()
        self.criado_em = criado_em
        # ENCAPSULAMENTO: o hash da senha é privado (__). Fora da classe não dá
        # para ler nem trocar por acaso; só pelos métodos abaixo.
        self.__senha_hash = senha_hash

    # ----- Encapsulamento da senha -----

    @classmethod
    def novo(cls, nome, email, senha):
        """Cria um usuário a partir da senha em texto puro (que nunca é guardada)."""
        usuario = cls(nome, email)
        usuario.definir_senha(senha)
        return usuario

    def definir_senha(self, senha):
        if not senha or len(senha) < 6:
            raise ValueError("A senha precisa ter pelo menos 6 caracteres.")
        self.__senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        if self.__senha_hash is None:
            return False
        return check_password_hash(self.__senha_hash, senha)

    # ----- Banco de dados (SQL puro) -----

    @classmethod
    def criar_tabela(cls):
        cls._executar(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nome        TEXT    NOT NULL,
                email       TEXT    NOT NULL UNIQUE,
                senha_hash  TEXT    NOT NULL,
                criado_em   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def salvar(self):
        if self.__senha_hash is None:
            raise ValueError("Defina a senha antes de salvar o usuário.")
        self.id = self._executar(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
            (self.nome, self.email, self.__senha_hash),
        )
        return self.id

    @classmethod
    def buscar_por_email(cls, email):
        linhas = cls._consultar(
            "SELECT id, nome, email, senha_hash, criado_em FROM usuarios WHERE email = ?",
            (email,),
        )
        return cls._de_linha(linhas[0]) if linhas else None

    @classmethod
    def buscar_por_id(cls, usuario_id):
        linhas = cls._consultar(
            "SELECT id, nome, email, senha_hash, criado_em FROM usuarios WHERE id = ?",
            (usuario_id,),
        )
        return cls._de_linha(linhas[0]) if linhas else None

    @classmethod
    def autenticar(cls, email, senha):
        """Devolve o Usuario se e-mail e senha conferem; senão, None."""
        usuario = cls.buscar_por_email((email or "").strip().lower())
        if usuario is None:
            check_password_hash(_HASH_FALSO, senha or "")
            return None
        return usuario if usuario.verificar_senha(senha or "") else None

    @classmethod
    def _de_linha(cls, linha):
        return cls(
            id=linha["id"],
            nome=linha["nome"],
            email=linha["email"],
            senha_hash=linha["senha_hash"],
            criado_em=linha["criado_em"],
        )

    # ----- Implementações dos métodos abstratos (polimorfismo) -----

    def validar(self):
        erros = []
        if not self.nome:
            erros.append("Informe o nome.")
        elif len(self.nome) > 120:
            erros.append("O nome pode ter no máximo 120 caracteres.")
        if not _PADRAO_EMAIL.match(self.email):
            erros.append("Informe um e-mail válido.")
        return erros

    def para_dict(self):
        # Repare: a senha NUNCA entra aqui, então nunca vaza para um JSON.
        return {"id": self.id, "nome": self.nome, "email": self.email, "criado_em": self.criado_em}

    def __str__(self):
        return f"{self.nome} <{self.email}>"
