import asyncio
import socket

from data_access.config import GameControllerConfig
from data_access.gc import MulticastRefereeSource, _membership
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


def test_membership_is_a_portable_ip_mreq():
    # 8-byte ip_mreq (group + INADDR_ANY): '4s4s' works on Linux and macOS/BSD,
    # unlike the 12-byte '4sl' form which the BSD stack rejects.
    m = _membership("224.5.23.1")
    assert len(m) == 8
    assert m[:4] == socket.inet_aton("224.5.23.1")
    assert m[4:] == socket.inet_aton("0.0.0.0")


def _decode_ok(payload: bytes) -> MatchState:
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team("B", payload[0], 0), Team("Y", 0, 0))


async def test_handle_decodes_and_yields():
    src = MulticastRefereeSource(GameControllerConfig("224.5.23.1", 10003), _decode_ok)
    src._handle(b"\x05")
    state = await asyncio.wait_for(src._queue.get(), timeout=1)
    assert state.blue.score == 5


async def test_handle_skips_on_decode_error():
    def boom(_):
        raise ValueError("bad")

    src = MulticastRefereeSource(GameControllerConfig("224.5.23.1", 10003), boom)
    src._handle(b"\x00")
    assert src._queue.empty()


async def test_stop_is_safe_before_start_and_closes_the_transport():
    src = MulticastRefereeSource(GameControllerConfig("224.5.23.1", 10003), _decode_ok)
    await src.stop()  # never started: no-op, must not raise

    class _Transport:
        closed = False

        def close(self):
            self.closed = True

    transport = _Transport()
    src._transport = transport
    await src.stop()
    assert transport.closed and src._transport is None
