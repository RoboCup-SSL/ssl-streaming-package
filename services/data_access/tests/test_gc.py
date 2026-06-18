import asyncio

from data_access.config import GameControllerConfig
from data_access.gc import MulticastRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


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
