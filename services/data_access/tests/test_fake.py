from data_access.fake import FakeRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


def _state(score):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team("B", score, 0), Team("Y", 0, 0))


async def test_fake_source_yields_states_in_order():
    src = FakeRefereeSource([(0.0, _state(0)), (0.0, _state(1))])
    seen = [s.blue.score async for s in src]
    assert seen == [0, 1]
