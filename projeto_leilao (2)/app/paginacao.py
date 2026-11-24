"""Paginação: uma classe que calcula tudo o que a tela precisa."""

import math


class Paginacao:
    def __init__(self, pagina, por_pagina, total):
        # Atributos "privados" (convenção __): só são lidos pelas properties abaixo.
        self.__por_pagina = max(1, int(por_pagina))
        self.__total = max(0, int(total))
        # Página pedida fora do intervalo (0, -3, 999) vira a mais próxima válida.
        self.__pagina = min(max(1, int(pagina or 1)), self.total_paginas)

    @property
    def pagina(self):
        return self.__pagina

    @property
    def por_pagina(self):
        return self.__por_pagina

    @property
    def total(self):
        return self.__total

    @property
    def total_paginas(self):
        return max(1, math.ceil(self.__total / self.__por_pagina))

    @property
    def offset(self):
        """Quantos registros pular no SQL (LIMIT ... OFFSET ...)."""
        return (self.__pagina - 1) * self.__por_pagina

    @property
    def tem_anterior(self):
        return self.__pagina > 1

    @property
    def tem_proxima(self):
        return self.__pagina < self.total_paginas

    @property
    def anterior(self):
        return self.__pagina - 1

    @property
    def proxima(self):
        return self.__pagina + 1

    def janela(self, vizinhas=2):
        """Números a mostrar: primeira, última e as vizinhas da atual. None = reticências."""
        ultima = self.total_paginas
        numeros = {1, ultima}
        numeros.update(range(self.__pagina - vizinhas, self.__pagina + vizinhas + 1))
        visiveis = sorted(n for n in numeros if 1 <= n <= ultima)

        resultado = []
        for numero in visiveis:
            if resultado and numero - resultado[-1] > 1:
                resultado.append(None)
            resultado.append(numero)
        return resultado
