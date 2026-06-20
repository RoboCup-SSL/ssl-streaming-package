from configuration.checks import config_warnings


def _write(tmp_path, body):
    p = tmp_path / "field.toml"
    p.write_text(body)
    return str(p)


def test_warns_on_unedited_password_and_placeholder_camera(tmp_path):
    path = _write(tmp_path, """
[obs]
url = "ws://localhost:4455"
password = "change-me"

[cameras]
field-1 = "rtsp://10.0.0.5:554/stream"
""")
    warnings = config_warnings(path)
    assert any("change-me" in w for w in warnings)
    assert any("example values" in w and "field-1" in w for w in warnings)


def test_warns_when_no_cameras(tmp_path):
    path = _write(tmp_path, """
[obs]
password = "real-secret"
""")
    warnings = config_warnings(path)
    assert any("no [cameras]" in w for w in warnings)


def test_clean_config_has_no_warnings(tmp_path):
    path = _write(tmp_path, """
[obs]
password = "real-secret"

[cameras]
commentator = "usb:/dev/video0"
""")
    assert config_warnings(path) == []
