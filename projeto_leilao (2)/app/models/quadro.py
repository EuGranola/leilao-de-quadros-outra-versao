"""Model Quadro (herda de ModeloBase).

Toda a comunicação com o banco relacionada a quadros fica AQUI, com SQL puro e
o módulo nativo `sqlite3`. As rotas (controllers) nunca escrevem SQL: só
instanciam a classe e chamam os métodos dela.

Métodos principais:
    conectar()      (herdado) abre uma conexão com o arquivo .db
    criar_tabela()  CREATE TABLE IF NOT EXISTS
    salvar()        INSERT INTO
    listar()        SELECT ... LIMIT ... OFFSET  (com paginação)
    contar()        SELECT COUNT(*)
    validar()       regras de negócio antes de salvar
"""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.models.base import ModeloBase

# Limite de preço: R$ 100.000.000,00 (em centavos).
PRECO_MAXIMO_CENTAVOS = 100_000_000 * 100


class Quadro(ModeloBase):
    TABELA = "quadros"

    def __init__(self, titulo, artista, preco_inicial, dono_id, ano=None,
                 tecnica=None, descricao=None, imagem=None,
                 id=None, criado_em=None, dono_nome=None):
        self.id = id
        self.titulo = (titulo or "").strip()
        self.artista = (artista or "").strip()
        self.ano = ano
        self.tecnica = (tecnica or "").strip() or None
        self.descricao = (descricao or "").strip() or None
        self.preco_inicial = preco_inicial   # passa pelo setter (property) abaixo
        self.imagem = imagem                 # nome do arquivo em static/uploads
        self.dono_id = dono_id
        self.criado_em = criado_em
        self.dono_nome = dono_nome           # vem do JOIN no listar()

    # ----- Encapsulamento do preço (guardado em centavos, inteiro) -----

    @property
    def preco_inicial(self):
        return self._preco_inicial

    @preco_inicial.setter
    def preco_inicial(self, valor):
        # None é aceito: significa "o formulário trouxe um preço inválido",
        # e esse erro já é reportado pelo controller.
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0):
            raise ValueError("O preço inicial precisa ser um inteiro de centavos maior que zero.")
        self._preco_inicial = valor

    @property
    def preco_formatado(self):
        """150050 -> 'R$ 1.500,50'."""
        if self._preco_inicial is None:
            return ""
        reais, centavos = divmod(self._preco_inicial, 100)
        return f"R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"

    # ----- Banco de dados (SQL puro) -----

    @classmethod
    def criar_tabela(cls):
        cls._executar(
            """
            CREATE TABLE IF NOT EXISTS quadros (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo         TEXT    NOT NULL,
                artista        TEXT    NOT NULL,
                ano            INTEGER,
                tecnica        TEXT,
                descricao      TEXT,
                preco_inicial  INTEGER NOT NULL CHECK (preco_inicial > 0),
                imagem         TEXT,
                dono_id        INTEGER NOT NULL REFERENCES usuarios(id),
                criado_em      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def salvar(self):
        """INSERT do objeto no banco. Preenche self.id e o devolve."""
        self.id = self._executar(
            """
            INSERT INTO quadros
                (titulo, artista, ano, tecnica, descricao, preco_inicial, imagem, dono_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.titulo, self.artista, self.ano, self.tecnica, self.descricao,
             self.preco_inicial, self.imagem, self.dono_id),
        )
        return self.id

    @classmethod
    def listar(cls, limite=None, offset=0):
        """SELECT dos quadros (mais recentes primeiro), já com o nome do dono.

        Com `limite`, devolve só uma página (LIMIT/OFFSET).
        """
        sql = """
            SELECT q.id, q.titulo, q.artista, q.ano, q.tecnica, q.descricao,
                   q.preco_inicial, q.imagem, q.dono_id, q.criado_em,
                   u.nome AS dono_nome
            FROM quadros AS q
            JOIN usuarios AS u ON u.id = q.dono_id
            ORDER BY q.criado_em DESC, q.id DESC
        """
        parametros = ()
        if limite is not None:
            sql += " LIMIT ? OFFSET ?"
            parametros = (limite, offset)
        return [cls._de_linha(linha) for linha in cls._consultar(sql, parametros)]

    @classmethod
    def contar(cls):
        """SELECT COUNT(*): total de quadros (necessário para a paginação)."""
        return cls._consultar("SELECT COUNT(*) AS total FROM quadros")[0]["total"]

    @classmethod
    def _de_linha(cls, linha):
        return cls(
            id=linha["id"],
            titulo=linha["titulo"],
            artista=linha["artista"],
            ano=linha["ano"],
            tecnica=linha["tecnica"],
            descricao=linha["descricao"],
            preco_inicial=linha["preco_inicial"],
            imagem=linha["imagem"],
            dono_id=linha["dono_id"],
            criado_em=linha["criado_em"],
            dono_nome=linha["dono_nome"],
        )

    # ----- Implementações dos métodos abstratos (polimorfismo) -----

    def validar(self):
        erros = []

        if not self.titulo:
            erros.append("Informe o título do quadro.")
        elif len(self.titulo) > 120:
            erros.append("O título pode ter no máximo 120 caracteres.")

        if not self.artista:
            erros.append("Informe o nome do artista.")
        elif len(self.artista) > 120:
            erros.append("O nome do artista pode ter no máximo 120 caracteres.")

        if self.ano is not None and not (1000 <= self.ano <= date.today().year):
            erros.append(f"O ano precisa estar entre 1000 e {date.today().year}.")

        if self.tecnica and len(self.tecnica) > 80:
            erros.append("A técnica pode ter no máximo 80 caracteres.")

        if self.descricao and len(self.descricao) > 2000:
            erros.append("A descrição pode ter no máximo 2000 caracteres.")

        return erros

    def para_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "artista": self.artista,
            "ano": self.ano,
            "tecnica": self.tecnica,
            "descricao": self.descricao,
            "preco_inicial_centavos": self.preco_inicial,
            "preco_inicial_formatado": self.preco_formatado,
            "imagem": self.imagem,
            "dono_id": self.dono_id,
            "dono_nome": self.dono_nome,
            "criado_em": self.criado_em,
        }

    def __str__(self):
        return f"“{self.titulo}” de {self.artista}"

    # ----- Conversões de texto (o formulário HTML sempre envia texto) -----

    @staticmethod
    def reais_para_centavos(texto):
        """'1500,50' / '1.500,50' / '1500.50' -> 150050. Levanta ValueError se inválido.

        Dinheiro é guardado em centavos (inteiro) para evitar erros de
        arredondamento de números decimais (float).
        """
        texto = (texto or "").strip()
        if not texto:
            raise ValueError("Informe o preço inicial.")

        if "," in texto:  # formato brasileiro: ponto separa milhar, vírgula separa centavos
            texto = texto.replace(".", "").replace(",", ".")

        try:
            valor = Decimal(texto)
        except InvalidOperation:
            raise ValueError("Preço inicial inválido. Use apenas números, como 1500,00.")

        if not valor.is_finite():
            raise ValueError("Preço inicial inválido. Use apenas números, como 1500,00.")

        centavos = int((valor * 100).to_integral_value(rounding=ROUND_HALF_UP))
        if centavos <= 0:
            raise ValueError("O preço inicial precisa ser maior que zero.")
        if centavos > PRECO_MAXIMO_CENTAVOS:
            raise ValueError("O preço inicial pode ser no máximo R$ 100.000.000,00.")
        return centavos

    @staticmethod
    def texto_para_ano(texto):
        """'1998' -> 1998; vazio -> None. Levanta ValueError se não for número."""
        texto = (texto or "").strip()
        if not texto:
            return None
        try:
            return int(texto)
        except ValueError:
            raise ValueError("O ano precisa ser um número, como 1998.")
