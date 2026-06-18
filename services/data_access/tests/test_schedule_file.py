import json

from data_access.schedule import ScheduleFile


def test_load_returns_last_good_on_invalid(tmp_path):
    p = tmp_path / "schedule.json"
    p.write_text(json.dumps({"schedule": [], "live": {}}))
    sf = ScheduleFile(str(p))
    first = sf.load()
    p.write_text("{ not valid json")
    assert sf.load() == first
