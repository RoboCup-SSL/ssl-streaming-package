import struct

from data_access.gamelog import GamelogRefereeSource, read_referee_messages
from data_processing.decode import decode_referee
from data_structures.proto import ssl_gc_referee_pb2 as pb

REFEREE, VISION = 3, 4


def _referee_record(blue_name, blue_score, ts_ns):
    ref = pb.Referee(stage=1, command=2, command_counter=1, command_timestamp=1)
    ref.blue.name, ref.blue.score = blue_name, blue_score
    ref.yellow.name = "Y"
    payload = ref.SerializeToString()
    return struct.pack(">qii", ts_ns, REFEREE, len(payload)) + payload


def _vision_record(ts_ns):
    payload = b"\x00\x01\x02"
    return struct.pack(">qii", ts_ns, VISION, len(payload)) + payload


def _write_log(tmp_path, *records, name="game.log"):
    path = tmp_path / name
    with open(path, "wb") as fh:
        fh.write(b"SSL_LOG_FILE")
        fh.write(struct.pack(">i", 1))
        for record in records:
            fh.write(record)
    return str(path)


def test_read_referee_messages_filters_vision_and_keeps_order(tmp_path):
    path = _write_log(
        tmp_path,
        _referee_record("B", 0, 1000),
        _vision_record(1500),
        _referee_record("B", 1, 2000),
    )
    msgs = list(read_referee_messages(path))
    assert [ts for ts, _ in msgs] == [1000, 2000]
    assert decode_referee(msgs[1][1]).blue.score == 1


def test_read_referee_messages_rejects_a_bad_header(tmp_path):
    bad = tmp_path / "bad.log"
    bad.write_bytes(b"NOT_A_LOG___" + b"\x00\x00\x00\x01")
    try:
        list(read_referee_messages(str(bad)))
        assert False, "expected ValueError"
    except ValueError:
        pass


async def test_gamelog_source_yields_decoded_states_with_scaled_gaps(tmp_path):
    path = _write_log(
        tmp_path,
        _referee_record("ZJUNlict", 0, 1_000_000_000),
        _referee_record("ZJUNlict", 1, 3_000_000_000),  # +2.0s
    )
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    src = GamelogRefereeSource(path, decode_referee, speed=2.0, sleep=fake_sleep)
    states = [s async for s in src]
    assert [s.blue.score for s in states] == [0, 1]
    assert sleeps == [1.0]  # first emits immediately; 2.0s gap / speed 2.0


async def test_gamelog_source_caps_long_gaps(tmp_path):
    path = _write_log(
        tmp_path,
        _referee_record("B", 0, 0),
        _referee_record("B", 1, 100_000_000_000),  # 100s gap
    )
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    src = GamelogRefereeSource(path, decode_referee, max_gap=2.0, sleep=fake_sleep)
    [s async for s in src]
    assert sleeps == [2.0]
