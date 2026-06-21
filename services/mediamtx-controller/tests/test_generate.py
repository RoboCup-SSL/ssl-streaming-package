import pytest

from mediamtx_controller.generate import CAMERA_NAMES, build_config


def test_build_config_has_all_five_fixed_paths():
    config = build_config({})
    assert set(config["paths"]) == set(CAMERA_NAMES)
    assert CAMERA_NAMES == ["commentator", "field-1", "field-2", "field-3", "field-4"]


def test_build_config_quiets_mediamtx_to_warnings():
    # Drops the per-listener/per-session INFO spam off the console; real
    # warnings/errors (and a failed start) stay visible.
    assert build_config({})["logLevel"] == "warn"


def test_build_config_disables_servers_we_dont_use():
    # We only use RTSP. Disabling the rest avoids extra open ports and stops MoQ
    # from writing a self-signed auto.crt/auto.key into the working directory.
    config = build_config({})
    assert all(config[server] is False for server in ("rtmp", "hls", "webrtc", "srt", "moq"))


def test_declared_cameras_get_a_source_others_are_blank():
    config = build_config({"field-1": "rtsp://cam/stream"})
    assert config["paths"]["field-1"] == {"source": "rtsp://cam/stream"}
    assert config["paths"]["field-2"] == {}  # defined but black until fed


def test_unknown_camera_name_raises():
    with pytest.raises(ValueError):
        build_config({"field-9": "rtsp://cam/stream"})
