from mediamtx_controller.cameras import load_cameras


def test_load_cameras_reads_the_cameras_table(tmp_path):
    toml = tmp_path / "field.toml"
    toml.write_text(
        """
[field]
name = "A"

[cameras]
commentator = "usb:/dev/video0"
field-1 = "rtsp://cam/stream"
"""
    )
    assert load_cameras(str(toml)) == {
        "commentator": "usb:/dev/video0",
        "field-1": "rtsp://cam/stream",
    }


def test_load_cameras_empty_when_absent(tmp_path):
    toml = tmp_path / "field.toml"
    toml.write_text('[field]\nname = "A"\n')
    assert load_cameras(str(toml)) == {}
