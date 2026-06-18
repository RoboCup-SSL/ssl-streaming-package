from data_structures.proto import ssl_gc_referee_pb2 as pb


def test_referee_roundtrip():
    ref = pb.Referee(stage=1, command=2, command_counter=7, command_timestamp=123)
    ref.yellow.name = "TIGERs"
    ref.yellow.score = 2
    ref.blue.name = "ER-Force"
    ref.blue.score = 1
    parsed = pb.Referee()
    parsed.ParseFromString(ref.SerializeToString())
    assert parsed.blue.name == "ER-Force"
    assert parsed.yellow.score == 2
    assert parsed.command == 2
