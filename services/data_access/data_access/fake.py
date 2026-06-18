import asyncio
from typing import AsyncIterator

from data_structures.domain import MatchState


class FakeRefereeSource:
    """In-process RefereeSource for tests/dev. Emits a scripted sequence with
    optional per-step delays (seconds). Sends nothing on the network."""

    def __init__(self, steps: list[tuple[float, MatchState]]) -> None:
        self._steps = steps

    async def __aiter__(self) -> AsyncIterator[MatchState]:
        for delay, state in self._steps:
            if delay:
                await asyncio.sleep(delay)
            yield state
