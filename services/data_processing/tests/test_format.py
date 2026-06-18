from data_processing.format import format_updates, stage_label
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage

SOURCES = {
    "blue_name": "txt_blue", "blue_score": "txt_blue_score",
    "yellow_name": "txt_yellow", "yellow_score": "txt_yellow_score",
    "stage": "txt_stage", "next_match": "txt_next", "countdown": "txt_cd",
}


def _state():
    return MatchState(
        stage=Stage.NORMAL_FIRST_HALF, command=Command.NORMAL_START,
        blue=Team("ER-Force", 1, 0), yellow=Team("TIGERs", 2, 0),
    )


def test_stage_label_is_human_readable():
    assert stage_label(Stage.NORMAL_HALF_TIME) == "Half Time"


def test_format_updates_maps_to_source_names():
    view = {"next": {"matchup": "A vs B"}, "countdown": "5:00"}
    out = format_updates(_state(), view, SOURCES)
    assert out["txt_blue"] == "ER-Force"
    assert out["txt_blue_score"] == "1"
    assert out["txt_yellow_score"] == "2"
    assert out["txt_stage"] == "First Half"
    assert out["txt_next"] == "A vs B"
    assert out["txt_cd"] == "5:00"


def test_format_updates_skips_unmapped_keys():
    out = format_updates(_state(), None, {"blue_name": "txt_blue"})
    assert out == {"txt_blue": "ER-Force"}
