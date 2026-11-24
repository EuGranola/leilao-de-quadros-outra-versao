from app.models.usuario import Usuario
from app.models.quadro import Quadro

# Lista de todos os models do sistema. A ORDEM importa: "quadros" tem chave
# estrangeira para "usuarios", então usuarios vem primeiro.
MODELOS = [Usuario, Quadro]
