# live/tests/test_app.py
import json
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    data = {
        "schedule": [
            {"id": "d1-A-1", "day": "2026-07-02", "division": "A", "field": "A",
             "time": "08:30", "label": "G1", "teamA": "TIGERs", "teamB": "Ri-one"},
            {"id": "d1-A-2", "day": "2026-07-02", "division": "A", "field": "A",
             "time": "10:00", "label": "G2", "teamA": "ZJUNLict", "teamB": "LUHBots"},
        ],
        "live": {"A": {"currentId": "d1-A-1"}},
    }
    p = tmp_path / "schedule.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    app = create_app(str(p))
    app.config.update(TESTING=True)
    return app.test_client()


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_field_returns_now_and_next(client):
    body = client.get("/field/A").get_json()
    assert body["now"]["matchup"] == "TIGERs vs Ri-one"
    assert body["next"]["matchup"] == "ZJUNLict vs LUHBots"
    assert body["division"] == "A"


def test_unknown_field_404(client):
    assert client.get("/field/B1").status_code == 404


def test_bad_current_id_422(client, tmp_path):
    # rewrite the file with a bad pointer; hot-reload must pick it up
    import os
    p = tmp_path / "schedule.json"
    d = json.loads(p.read_text())
    d["live"]["A"]["currentId"] = "nope"
    p.write_text(json.dumps(d), encoding="utf-8")
    # force a distinct mtime so the mtime-based hot-reload definitely re-reads
    # (two writes in the same second can share an mtime on coarse filesystems)
    future = os.path.getmtime(p) + 10
    os.utime(p, (future, future))
    assert client.get("/field/A").status_code == 422


def test_serves_last_good_data_on_malformed_save(client, tmp_path):
    import os
    # baseline: a good read populates the cache
    assert client.get("/field/A").status_code == 200
    # simulate a mid-edit malformed save to the same file
    p = tmp_path / "schedule.json"
    p.write_text("{ this is not valid json", encoding="utf-8")
    future = os.path.getmtime(p) + 10
    os.utime(p, (future, future))
    # must keep serving the last-good data, NOT 500
    r = client.get("/field/A")
    assert r.status_code == 200
    assert r.get_json()["now"]["matchup"] == "TIGERs vs Ri-one"
