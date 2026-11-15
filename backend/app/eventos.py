"""Aviso en tiempo real a la web (Server-Sent Events) y límites de la demo."""

import asyncio
from collections import defaultdict, deque

from app.reloj import Reloj


class Difusor:
    """Reparte los eventos de un cobro a las páginas que lo están mirando."""

    def __init__(self) -> None:
        self._suscriptores: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def suscribir(self, cobro_id: str) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue()
        self._suscriptores[cobro_id].add(cola)
        return cola

    def cancelar(self, cobro_id: str, cola: asyncio.Queue) -> None:
        self._suscriptores[cobro_id].discard(cola)
        if not self._suscriptores[cobro_id]:
            self._suscriptores.pop(cobro_id, None)

    def publicar(self, cobro_id: str, evento: str, datos: dict) -> None:
        for cola in list(self._suscriptores.get(cobro_id, ())):
            cola.put_nowait((evento, datos))


class LimitePorIp:
    """Ventana deslizante de 60 s por IP, con el reloj inyectado (spec 001, RF-034).

    Un uso sale al cumplir 60 s. Así el reloj de pruebas reabre el límite con
    avanzar(60), sin esperar tiempo real.
    """

    def __init__(self, maximo_por_minuto: int, reloj: Reloj) -> None:
        self._maximo = maximo_por_minuto
        self._reloj = reloj
        self._usos: dict[str, deque[float]] = defaultdict(deque)

    def permitir(self, ip: str) -> bool:
        """True si esa IP todavía puede crear un cobro en la ventana."""
        ahora = self._reloj.ahora()
        usos = self._usos[ip]
        while usos and ahora - usos[0] >= 60:
            usos.popleft()
        if len(usos) >= self._maximo:
            return False
        usos.append(ahora)
        return True


class LimiteDeCanales:
    """Canales abiertos a la vez por IP (spec 001, RF-041)."""

    def __init__(self, maximo: int) -> None:
        self._maximo = maximo
        self._abiertos: dict[str, int] = defaultdict(int)

    def ocupar(self, ip: str) -> bool:
        """Reserva un canal. False si esa IP ya llegó al máximo."""
        if self._abiertos[ip] >= self._maximo:
            return False
        self._abiertos[ip] += 1
        return True

    def liberar(self, ip: str) -> None:
        """Suelta un canal. No baja de cero si ya no había ninguno."""
        if self._abiertos[ip] > 0:
            self._abiertos[ip] -= 1
