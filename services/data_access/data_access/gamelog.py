"""Replay an official SSL gamelog as a RefereeSource — the real-data counterpart to
FakeRefereeSource, with no network involved.

SSL log format (big-endian): 12-byte "SSL_LOG_FILE" + int32 version, then records of
int64 timestamp_ns, int32 message_type, int32 length, length bytes of payload.
Message type 3 is the Referee protobuf. Compressed logs (.gz) are read transparently.
"""
import asyncio
import gzip
import struct
from typing import AsyncIterator, Awaitable, Callable, Iterator

from data_structures.domain import MatchState

_HEADER = b"SSL_LOG_FILE"
_REFEREE = 3
Decode = Callable[[bytes], MatchState]


def _open(path: str):
    return gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")


def read_referee_messages(path: str) -> Iterator[tuple[int, bytes]]:
    """Yield (timestamp_ns, payload) for each referee message in the log, in order.
    Vision and other message types are skipped."""
    with _open(path) as fh:
        if fh.read(len(_HEADER)) != _HEADER:
            raise ValueError(f"{path}: not an SSL gamelog (missing {_HEADER!r} header)")
        fh.read(4)  # version
        while True:
            head = fh.read(16)
            if len(head) < 16:
                return
            timestamp, message_type, length = struct.unpack(">qii", head)
            payload = fh.read(length)
            if message_type == _REFEREE:
                yield timestamp, payload


class GamelogRefereeSource:
    """RefereeSource that replays a gamelog's referee messages with their original
    spacing (scaled by `speed`, individual gaps capped at `max_gap` so long stoppages
    don't stall a demo). `decode` is injected so this module depends only on
    data_structures, like MulticastRefereeSource."""

    def __init__(
        self,
        path: str,
        decode: Decode,
        speed: float = 1.0,
        max_gap: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._path = path
        self._decode = decode
        self._speed = speed
        self._max_gap = max_gap
        self._sleep = sleep

    async def __aiter__(self) -> AsyncIterator[MatchState]:
        previous_ts: int | None = None
        for timestamp, payload in read_referee_messages(self._path):
            if previous_ts is not None:
                gap = (timestamp - previous_ts) / 1e9 / self._speed
                await self._sleep(min(max(gap, 0.0), self._max_gap))
            previous_ts = timestamp
            yield self._decode(payload)
