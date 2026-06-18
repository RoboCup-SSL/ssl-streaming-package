from configuration.appconfig import FieldConfig


def test_load_from_file(tmp_path):
    toml = tmp_path / "field.toml"
    toml.write_text(
        """
[field]
name = "A"

[game_controller]
address = "224.5.23.1"
port = 10003

[obs]
url = "ws://localhost:4455"
password = "secret"

[obs.sources]
blue_name = "txt_blue"
stage = "txt_stage"

[schedule]
path = "data/schedule.json"
"""
    )
    cfg = FieldConfig.load_from_file(str(toml))
    assert cfg.name == "A"
    assert cfg.game_controller.port == 10003
    assert cfg.obs.sources["blue_name"] == "txt_blue"
    assert cfg.schedule.path == "data/schedule.json"
