import os

from data_access.fake import FakeRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from obs_live_data.app import effective_logos_dir, run_referee


def test_effective_logos_dir_resolves_relative_to_base_dir(tmp_path):
    bundle = tmp_path / "obs-live-data" / "logos"
    bundle.mkdir(parents=True)
    base = str(tmp_path / "obs-live-data")
    assert effective_logos_dir("logos", "", base) == str(bundle)


def test_effective_logos_dir_keeps_absolute_dir(tmp_path):
    assert effective_logos_dir("/abs/logos", "", str(tmp_path)) == "/abs/logos"


def test_effective_logos_dir_empty_uses_bundled(tmp_path):
    # An unset logos_dir falls back to the bundled package logos, independent of cwd/base.
    resolved = effective_logos_dir("", "", str(tmp_path))
    assert resolved.endswith("obs-live-data/logos")
    assert os.path.exists(os.path.join(resolved, "no-logo.png"))


class RecordingObs:
    def __init__(self):
        self.calls = []
        self.images = []

    async def set_text(self, source_name, value):
        self.calls.append((source_name, value))

    async def set_image(self, source_name, path):
        self.images.append((source_name, path))


def _state(blue_score, blue_name="ER-Force", yellow_name="TIGERs"):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team(blue_name, blue_score, 0), Team(yellow_name, 0, 0))


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


async def test_run_pushes_team_logos(tmp_path):
    (tmp_path / "er-force.png").write_bytes(b"x")
    (tmp_path / "no-logo.png").write_bytes(b"x")
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0, yellow_name="Nonexistent"))])
    await run_referee(
        src, obs, {}, {"blue_logo": "img_b", "yellow_logo": "img_y"}, str(tmp_path)
    )
    assert obs.images == [
        ("img_b", os.path.abspath(str(tmp_path / "er-force.png"))),
        ("img_y", os.path.abspath(str(tmp_path / "no-logo.png"))),
    ]
