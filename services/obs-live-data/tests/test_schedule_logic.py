# live/tests/test_schedule_logic.py
from datetime import datetime

import pytest

from schedule_logic import resolve, format_countdown

# Minimal fixture: Field A has 2 matches; Field B0 has 1. Note both A and B0
# reuse label "G1" on purpose — resolve must scope by field, not label.
DATA = {
    "schedule": [
        {"id": "d1-A-1", "day": "2026-07-02", "division": "A", "field": "A",
         "time": "08:30", "label": "G1", "teamA": "TIGERs", "teamB": "Ri-one"},
        {"id": "d1-A-2", "day": "2026-07-02", "division": "A", "field": "A",
         "time": "10:00", "label": "G2", "teamA": "ZJUNLict", "teamB": "LUHBots"},
        {"id": "d1-B0-1", "day": "2026-07-02", "division": "B", "field": "B0",
         "time": "08:30", "label": "G1", "teamA": "The Bots", "teamB": "GreenTea"},
    ],
    "live": {"A": {"currentId": "d1-A-1"}, "B0": {"currentId": "d1-B0-1"}},
}


def test_now_next_and_countdown():
    # 09:00 → 60 min before the 10:00 next match on field A
    r = resolve(DATA, "A", datetime(2026, 7, 2, 9, 0))
    assert r["field"] == "A"
    assert r["division"] == "A"
    assert r["now"]["matchup"] == "TIGERs vs Ri-one"
    assert r["next"]["matchup"] == "ZJUNLict vs LUHBots"
    assert r["secondsUntilNext"] == 3600
    assert r["countdown"] == "1:00:00"


def test_field_scoping_not_label():
    # B0's "G1" is a different match than A's "G1"
    r = resolve(DATA, "B0", datetime(2026, 7, 2, 7, 0))
    assert r["division"] == "B"
    assert r["now"]["matchup"] == "The Bots vs GreenTea"
    assert r["next"] is None  # only one match on B0


def test_overdue_clamps_to_zero():
    # 10:30 is past the 10:00 next match → clamp, never negative
    r = resolve(DATA, "A", datetime(2026, 7, 2, 10, 30))
    assert r["secondsUntilNext"] == 0
    assert r["countdown"] == "0:00"


def test_last_match_has_no_next():
    data = {**DATA, "live": {"A": {"currentId": "d1-A-2"}}}
    r = resolve(data, "A", datetime(2026, 7, 2, 11, 0))
    assert r["next"] is None
    assert r["secondsUntilNext"] is None
    assert r["countdown"] is None


def test_next_starts_at_override():
    data = {**DATA, "live": {"A": {"currentId": "d1-A-1", "nextStartsAt": "2026-07-02T09:30"}}}
    r = resolve(data, "A", datetime(2026, 7, 2, 9, 0))
    assert r["secondsUntilNext"] == 1800
    assert r["countdown"] == "30:00"


def test_unknown_field_raises():
    with pytest.raises(ValueError, match="unknown field"):
        resolve(DATA, "B1", datetime(2026, 7, 2, 9, 0))


def test_bad_current_id_raises():
    data = {**DATA, "live": {"A": {"currentId": "nope"}}}
    with pytest.raises(ValueError, match="currentId"):
        resolve(data, "A", datetime(2026, 7, 2, 9, 0))


@pytest.mark.parametrize("seconds,text", [
    (None, None),
    (0, "0:00"),
    (5, "0:05"),
    (412, "6:52"),
    (3600, "1:00:00"),
    (5400, "1:30:00"),
    (-10, "0:00"),
])
def test_format_countdown(seconds, text):
    assert format_countdown(seconds) == text


def test_next_id_override_selects_specific_match():
    data = {
        "schedule": DATA["schedule"] + [
            {"id": "d1-A-3", "day": "2026-07-02", "division": "A", "field": "A",
             "time": "11:30", "label": "G1", "teamA": "TIGERs", "teamB": "ER-Force"},
        ],
        "live": {"A": {"currentId": "d1-A-1", "nextId": "d1-A-3"}},
    }
    r = resolve(data, "A", datetime(2026, 7, 2, 9, 0))
    # natural next would be d1-A-2 (10:00); nextId forces d1-A-3 instead
    assert r["next"]["matchup"] == "TIGERs vs ER-Force"


def test_missing_current_id_raises_clear_error():
    data = {**DATA, "live": {"A": {}}}  # field present but no currentId configured
    with pytest.raises(ValueError, match="currentId"):
        resolve(data, "A", datetime(2026, 7, 2, 9, 0))


def test_next_selection_crosses_day_boundary():
    data = {
        "schedule": [
            {"id": "d1-A-9", "day": "2026-07-02", "division": "A", "field": "A",
             "time": "20:30", "label": "G2", "teamA": "KIKS", "teamB": "RoboCin"},
            {"id": "d2-A-1", "day": "2026-07-03", "division": "A", "field": "A",
             "time": "08:30", "label": "G1", "teamA": "ER-Force", "teamB": "Ri-one"},
        ],
        "live": {"A": {"currentId": "d1-A-9"}},
    }
    r = resolve(data, "A", datetime(2026, 7, 2, 21, 0))
    assert r["now"]["matchup"] == "KIKS vs RoboCin"
    assert r["next"]["matchup"] == "ER-Force vs Ri-one"  # next day, not mis-sorted
