from data_access.config import GameControllerConfig
from data_processing.decode import decode_referee
from obs_live_data.__main__ import build_source


def test_build_source_injects_real_decoder():
    src = build_source(GameControllerConfig("224.5.23.1", 10003))
    assert src._decode is decode_referee
