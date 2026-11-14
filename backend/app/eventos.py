"""Aviso en tiempo real a la web (Server-Sent Events) y límite de peticiones por IP."""

import asyncio
import time
from collections import defaultdict, deque


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
    """Ventana deslizante de un minuto. Suficiente para una demo con un solo proceso."""

    def __init__(self, maximo_por_minuto: int) -> None:
        self._maximo = maximo_por_minuto
        self._usos: dict[str, deque[float]] = defaultdict(deque)

    def permitir(self, ip: str) -> bool:
        ahora = time.monotonic()
        usos = self._usos[ip]
        while usos and ahora - usos[0] > 60:
            usos.popleft()
        if len(usos) >= self._maximo:
            return False
        usos.append(ahora)
        return True
