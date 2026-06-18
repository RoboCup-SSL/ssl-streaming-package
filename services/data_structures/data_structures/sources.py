from typing import AsyncIterator, Protocol

from data_structures.domain import MatchState


class RefereeSource(Protocol):
    def __aiter__(self) -> AsyncIterator[MatchState]: ...
