import pytest

from mediamtx_controller.paths import path_config


def test_rtsp_descriptor_is_a_direct_source():
    assert path_config("field-1", "rtsp://10.0.0.5:554/stream") == {
        "source": "rtsp://10.0.0.5:554/stream"
    }


def test_usb_descriptor_runs_ffmpeg_v4l2_publishing_to_the_path():
    cfg = path_config("commentator", "usb:/dev/video0", rtsp_port=8554)
    cmd = cfg["runOnInit"]
    assert "-f v4l2" in cmd
    assert "/dev/video0" in cmd
    assert "rtsp://localhost:8554/commentator" in cmd
    assert cfg["runOnInitRestart"] is True


def test_ffmpeg_children_are_quiet():
    # Quiet flags keep the console readable: no banner, no rewriting progress line,
    # no broken-pipe teardown spew — but a camera that can't open still reports.
    cmd = path_config("commentator", "usb:/dev/video0")["runOnInit"]
    for flag in ("-hide_banner", "-loglevel fatal", "-nostdin", "-nostats"):
        assert flag in cmd


def test_ts_descriptor_runs_ffmpeg_reading_the_url():
    cfg = path_config("field-2", "ts:udp://@:1234", rtsp_port=8554)
    cmd = cfg["runOnInit"]
    assert "udp://@:1234" in cmd
    assert "rtsp://localhost:8554/field-2" in cmd
    assert cfg["runOnInitRestart"] is True


def test_unknown_descriptor_raises():
    with pytest.raises(ValueError):
        path_config("field-1", "carrierpigeon:foo")
