import asyncio
import logging
import socket
import struct
from typing import AsyncIterator, Callable

from data_access.config import GameControllerConfig
from data_structures.domain import MatchState

log = logging.getLogger(__name__)

Decode = Callable[[bytes], MatchState]


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, handle: Callable[[bytes], None]) -> None:
        self._handle = handle

    def datagram_received(self, data: bytes, addr) -> None:
        self._handle(data)


class MulticastRefereeSource:
    """RefereeSource backed by the GC multicast feed. `decode` is injected so this
    module depends only on data_structures."""

    def __init__(self, config: GameControllerConfig, decode: Decode) -> None:
        self._config = config
        self._decode = decode
        self._queue: asyncio.Queue[MatchState] = asyncio.Queue()
        self._transport: asyncio.BaseTransport | None = None

    def _handle(self, payload: bytes) -> None:
        try:
            state = self._decode(payload)
        except Exception:
            log.warning("skipping undecodable referee datagram", exc_info=True)
            return
        self._queue.put_nowait(state)

    async def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self._config.port))
        membership = struct.pack(
            "4sl", socket.inet_aton(self._config.address), socket.INADDR_ANY
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        sock.setblocking(False)
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _Protocol(self._handle), sock=sock
        )

    async def __aiter__(self) -> AsyncIterator[MatchState]:
        while True:
            yield await self._queue.get()
