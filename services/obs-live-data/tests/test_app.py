from data_access.fake import FakeRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from obs_live_data.app import run_referee


class RecordingObs:
    def __init__(self):
        self.calls = []

    async def set_text(self, source_name, value):
        self.calls.append((source_name, value))


def _state(blue_score):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team("ER-Force", blue_score, 0), Team("TIGERs", 0, 0))


async def test_run_pushes_only_changed_fields():
    sources = {"blue_score": "txt_bs", "blue_name": "txt_bn"}
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0)), (0.0, _state(1))])
    await run_referee(src, obs, sources)
    # first state pushes both (format order: name before score); second state
    # re-pushes only the changed score.
    assert obs.calls == [
        ("txt_bn", "ER-Force"), ("txt_bs", "0"), ("txt_bs", "1"),
    ]
