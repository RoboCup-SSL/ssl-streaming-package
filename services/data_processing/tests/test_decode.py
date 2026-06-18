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
