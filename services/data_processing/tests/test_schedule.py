from datetime import datetime

from data_processing.schedule import format_countdown, resolve

DATA = {
    "schedule": [
        {"id": "m1", "day": "2026-07-02", "division": "A", "field": "A",
         "time": "08:30", "label": "G1", "teamA": "TIGERs", "teamB": "Ri-one"},
        {"id": "m2", "day": "2026-07-02", "division": "A", "field": "A",
         "time": "10:00", "label": "G2", "teamA": "ZJUNLict", "teamB": "LUHBots"},
    ],
    "live": {"A": {"currentId": "m1"}},
}


def test_resolve_now_next_countdown():
    out = resolve(DATA, "A", datetime(2026, 7, 2, 9, 0))
    assert out["now"]["matchup"] == "TIGERs vs Ri-one"
    assert out["next"]["matchup"] == "ZJUNLict vs LUHBots"
    assert out["countdown"] == "1:00:00"


def test_format_countdown_clamps_and_formats():
    assert format_countdown(None) is None
    assert format_countdown(-5) == "0:00"
    assert format_countdown(3661) == "1:01:01"
