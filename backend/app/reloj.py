"""Reloj inyectable para no esperar tiempo real en las pruebas (spec 001, principio V)."""

import asyncio
import time


class Reloj:
    """Hora real del sistema (spec 001, principio V; DP-4, R-2)."""

    def ahora(self) -> float:
        """Segundos Unix actuales."""
        return time.time()

    async def dormir(self, segundos: float) -> None:
        """Espera `segundos` de tiempo real."""
        await asyncio.sleep(segundos)


class RelojFalso(Reloj):
    """Reloj que solo avanza cuando la prueba se lo pide (spec 001, principio V)."""

    def __init__(self, inicio: float) -> None:
        self._ahora = inicio

    def ahora(self) -> float:
        """Segundos Unix fijados, sin leer el reloj del sistema."""
        return self._ahora

    def avanzar(self, segundos: float) -> None:
        """Adelanta el reloj `segundos`, sin esperar."""
        self._ahora += segundos

    async def dormir(self, segundos: float) -> None:
        """Adelanta el reloj y cede el control, sin esperar tiempo real."""
        self.avanzar(segundos)
        await asyncio.sleep(0)
