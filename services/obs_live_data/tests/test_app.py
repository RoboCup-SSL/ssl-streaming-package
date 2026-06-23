import os

from data_access.fake import FakeRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from obs_live_data.app import effective_logos_dir, run_referee


def test_effective_logos_dir_resolves_relative_to_base_dir(tmp_path):
    bundle = tmp_path / "obs_live_data" / "logos"
    bundle.mkdir(parents=True)
    base = str(tmp_path / "obs_live_data")
    assert effective_logos_dir("logos", "", base) == str(bundle)


def test_effective_logos_dir_keeps_absolute_dir(tmp_path):
    assert effective_logos_dir("/abs/logos", "", str(tmp_path)) == "/abs/logos"


def test_effective_logos_dir_empty_uses_bundled(tmp_path):
    # An unset logos_dir falls back to the bundled package logos, independent of cwd/base.
    resolved = effective_logos_dir("", "", str(tmp_path))
    assert resolved.endswith("obs_live_data/logos")
    assert os.path.exists(os.path.join(resolved, "no-logo.png"))


class RecordingObs:
    def __init__(self):
        self.calls = []
        self.images = []
        self.colors = []

    async def set_text(self, source_name, value):
        self.calls.append((source_name, value))

    async def set_image(self, source_name, path):
        self.images.append((source_name, path))

    async def set_color(self, source_name, color):
        self.colors.append((source_name, color))


def _state(blue_score, blue_name="ER-Force", yellow_name="TIGERs"):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team(blue_name, blue_score, 0), Team(yellow_name, 0, 0))


async def test_run_pushes_changed_fields_only():
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0)), (0.0, _state(1))])
    await run_referee(src, obs, "logos")
    # canonical source names; blue_score re-pushes on change, blue_name does not.
    assert ("blue_name", "ER-Force") in obs.calls
    assert obs.calls.count(("blue_name", "ER-Force")) == 1
    assert obs.calls.count(("blue_score", "0")) == 1
    assert obs.calls.count(("blue_score", "1")) == 1


async def test_run_pushes_command_color_for_the_active_team():
    obs = RecordingObs()
    blue_bp = MatchState(Stage.NORMAL_FIRST_HALF, Command.BALL_PLACEMENT_BLUE,
                         Team("B", 0, 0), Team("Y", 0, 0))
    src = FakeRefereeSource([(0.0, blue_bp)])
    await run_referee(src, obs, "logos")
    assert ("command_color", 0xFFFF9F77) in obs.colors


async def test_run_pushes_team_logos(tmp_path):
    (tmp_path / "er-force.png").write_bytes(b"x")
    (tmp_path / "no-logo.png").write_bytes(b"x")
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0, yellow_name="Nonexistent"))])
    await run_referee(src, obs, str(tmp_path))
    assert obs.images == [
        ("blue_logo", os.path.abspath(str(tmp_path / "er-force.png"))),
        ("yellow_logo", os.path.abspath(str(tmp_path / "no-logo.png"))),
    ]
