from data_processing.decode import decode_referee
from data_structures.enums import Command, Stage
from data_structures.proto import ssl_gc_referee_pb2 as pb


def _payload():
    ref = pb.Referee(stage=4, command=15, command_counter=3, command_timestamp=9)
    ref.blue.name, ref.blue.score, ref.blue.yellow_cards = "ER-Force", 1, 0
    ref.yellow.name, ref.yellow.score, ref.yellow.yellow_cards = "TIGERs", 2, 1
    return ref.SerializeToString()


def test_decode_referee_maps_fields():
    state = decode_referee(_payload())
    assert state.stage is Stage.NORMAL_SECOND_HALF
    assert state.command is Command.GOAL_BLUE
    assert state.blue.name == "ER-Force" and state.blue.score == 1
    assert state.yellow.name == "TIGERs" and state.yellow.yellow_cards == 1


def _full_payload():
    ref = pb.Referee(stage=1, command=16, command_counter=1, command_timestamp=1)
    ref.stage_time_left = 123_000_000
    ref.next_command = 9  # DIRECT_FREE_BLUE
    ref.current_action_time_remaining = -5_000_000
    ref.blue.name, ref.blue.score, ref.blue.yellow_cards = "ER-Force", 1, 1
    ref.blue.red_cards = 2
    ref.blue.yellow_card_times.extend([5_000_000, 9_000_000])
    ref.blue.timeout_time = 240_000_000
    ref.blue.bot_substitution_intent = True
    ref.yellow.name, ref.yellow.score, ref.yellow.yellow_cards = "TIGERs", 2, 0
    ref.yellow.bot_substitution_allowed = True
    ref.yellow.bot_substitution_time_left = 18_000_000
    return ref.SerializeToString()


def test_decode_referee_maps_new_fields():
    state = decode_referee(_full_payload())
    assert state.stage_time_left == 123_000_000
    assert state.next_command is Command.DIRECT_FREE_BLUE
    assert state.action_time_remaining == -5_000_000
    assert state.blue.red_cards == 2
    assert state.blue.yellow_card_times == (5_000_000, 9_000_000)
    assert state.blue.timeout_time == 240_000_000
    assert state.blue.substitution_intent is True
    assert state.yellow.substitution_allowed is True
    assert state.yellow.substitution_time_left == 18_000_000


def test_decode_referee_next_command_absent_is_none():
    ref = pb.Referee(stage=1, command=0, command_counter=1, command_timestamp=1)
    ref.blue.name, ref.yellow.name = "B", "Y"
    assert decode_referee(ref.SerializeToString()).next_command is None
