from data_processing.format import (
    card_time_texts,
    command_text,
    format_clock,
    format_updates,
    next_command_text,
    stage_label,
    substitution_text,
)
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


def _state(**kw):
    base = dict(
        stage=Stage.NORMAL_FIRST_HALF, command=Command.NORMAL_START,
        blue=Team("ER-Force", 1, 0), yellow=Team("TIGERs", 2, 0),
    )
    base.update(kw)
    return MatchState(**base)


def test_format_clock_zero_and_padding():
    assert format_clock(0) == "0:00"
    assert format_clock(8_000_000) == "00:08"
    assert format_clock(125_000_000) == "02:05"


def test_format_clock_ceils_and_signs():
    assert format_clock(1_200_000) == "00:02"      # ceil of 1.2s
    assert format_clock(-5_000_000) == "-00:05"


def test_stage_label_uses_board_wording():
    assert stage_label(Stage.NORMAL_FIRST_HALF) == "1st Half"
    assert stage_label(Stage.NORMAL_HALF_TIME) == "Half Time"
    assert stage_label(Stage.POST_GAME) == "Match finished"


def test_command_text_embeds_team_and_inline_times():
    assert command_text(_state(command=Command.DIRECT_FREE_BLUE)) == "Free Kick for Blue"
    assert command_text(_state(command=Command.HALT)) == "Halt"
    bp = _state(command=Command.BALL_PLACEMENT_BLUE, action_time_remaining=8_000_000)
    assert command_text(bp) == "Ball Placement for Blue (00:08)"
    to = _state(command=Command.TIMEOUT_YELLOW,
                yellow=Team("TIGERs", 2, 0, timeout_time=83_000_000))
    assert command_text(to) == "Timeout for Yellow (01:23)"


def test_next_command_text():
    assert next_command_text(None) == ""
    assert next_command_text(Command.PREPARE_KICKOFF_YELLOW) == "Next: Kickoff for Yellow"


def test_substitution_text():
    assert substitution_text(Team("B", 0, 0)) == ""
    assert substitution_text(Team("B", 0, 0, substitution_intent=True)) == "Substitution Requested"
    active = Team("B", 0, 0, substitution_allowed=True, substitution_time_left=18_000_000)
    assert substitution_text(active) == "Substitution Active (00:18)"


def test_card_time_texts_caps_at_two():
    team = Team("B", 0, 0, yellow_card_times=(5_000_000, 9_000_000, 12_000_000))
    assert card_time_texts(team) == ["00:05", "00:09"]
    assert card_time_texts(Team("B", 0, 0)) == []


def test_format_updates_emits_all_canonical_keys():
    out = format_updates(_state(
        stage_time_left=125_000_000,
        blue=Team("ER-Force", 1, 1, red_cards=2, yellow_card_times=(5_000_000,)),
    ))
    assert out["blue_name"] == "ER-Force"
    assert out["blue_score"] == "1"
    assert out["yellow_score"] == "2"
    assert out["stage"] == "1st Half"
    assert out["stage_time"] == "02:05"
    assert out["command"] == "Normal Start"
    assert out["next_command"] == ""
    assert out["blue_yellow_cards"] == "1"
    assert out["blue_red_cards"] == "2"
    assert out["blue_card_time_1"] == "00:05"
    assert out["blue_card_time_2"] == ""      # blank-filled to two
    assert out["yellow_card_time_1"] == ""
    assert out["blue_substitution"] == ""
