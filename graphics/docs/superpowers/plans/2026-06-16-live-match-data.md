# Live Match Data → OBS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **PROJECT RULE — NO GIT:** This repo forbids git operations (save to disk only; never commit/branch/push). Every task ends with a **"run the full test suite"** checkpoint instead of a commit. Do not run `git` at all.

**Goal:** A small Flask server that reads one manually-edited schedule file and serves per-field "now / next / countdown" JSON, which OBS pulls via the `obs-urlsource` plugin and renders as native text across the three fields.

**Architecture:** `data/schedule.json` (operator edits a per-field `currentId` pointer) → Flask re-reads it on mtime change → pure `schedule_logic.resolve()` computes now/next/countdown → REST endpoints `/field/A|B0|B1` return ready-to-render strings → OBS `obs-urlsource` text sources poll and render. Divisions: Field A = Division A; Fields B0+B1 = Division B. Group labels and playoff codes repeat across divisions, so matches are keyed by field (which implies division) and never deduped by label.

**Tech Stack:** Python 3 (already present), Flask, pytest. No frontend/build step. Spec: `docs/superpowers/specs/2026-06-16-live-match-data-design.md`.

**Import note:** `live/` is NOT a package. `app.py`, `import_schedule.py`, and tests import sibling modules directly (`from schedule_logic import ...`); `live/conftest.py` puts the `live/` dir on `sys.path` so pytest resolves them. Run tests from the repo root with `python -m pytest live -v`.

---

### Task 1: Scaffold `live/` and install dependencies

**Files:**
- Create: `live/requirements.txt`
- Create: `live/conftest.py`
- Create: `live/data/.gitkeep` (empty; the data dir must exist before the importer runs)

- [ ] **Step 1: Create `live/requirements.txt`**

```
flask>=3.0
pytest>=8.0
```

- [ ] **Step 2: Create `live/conftest.py`** (lets tests import sibling modules without packaging)

```python
import os
import sys

# Put the live/ directory on sys.path so tests can `from schedule_logic import ...`.
sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 3: Create the data dir placeholder**

Create an empty file `live/data/.gitkeep` (contents: one empty line). The importer writes `live/data/schedule.json` here in Task 3.

- [ ] **Step 4: Install dependencies**

Run: `pip install -r live/requirements.txt`
Expected: Flask and pytest install successfully.

- [ ] **Step 5: Verify pytest runs (no tests yet)**

Run: `python -m pytest live -v`
Expected: exits cleanly with "no tests ran" (collected 0 items). Confirms `conftest.py` loads.

---

### Task 2: Pure schedule logic (`resolve` + `format_countdown`)

This is the only unit-tested layer (project convention). Build it test-first.

**Files:**
- Create: `live/schedule_logic.py`
- Test: `live/tests/test_schedule_logic.py`

- [ ] **Step 1: Write the failing test file**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest live/tests/test_schedule_logic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'schedule_logic'`.

- [ ] **Step 3: Write the implementation**

```python
# live/schedule_logic.py
from datetime import datetime


def _match_dt(m):
    """Absolute datetime of a match from its day + time (venue-local)."""
    return datetime.strptime(f'{m["day"]} {m["time"]}', "%Y-%m-%d %H:%M")


def _view(m):
    """Public match view with a ready-to-render matchup string."""
    return {
        "label": m["label"],
        "teamA": m["teamA"],
        "teamB": m["teamB"],
        "time": m["time"],
        "matchup": f'{m["teamA"]} vs {m["teamB"]}',
    }


def format_countdown(seconds):
    """None -> None. Else clamp >=0 and format M:SS (<1h) or H:MM:SS (>=1h)."""
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def resolve(data, field, now_dt):
    """Given loaded schedule data, a field, and 'now', return the field's
    now/next/countdown payload. Raises ValueError on unknown field or bad currentId."""
    field_matches = sorted(
        (m for m in data["schedule"] if m["field"] == field),
        key=_match_dt,
    )
    if not field_matches:
        raise ValueError(f"unknown field: {field!r}")

    live = data.get("live", {}).get(field, {})
    current_id = live.get("currentId")
    now_match = next((m for m in field_matches if m["id"] == current_id), None)
    if now_match is None:
        raise ValueError(f"currentId {current_id!r} not found for field {field!r}")

    next_id = live.get("nextId")
    if next_id is not None:
        next_match = next((m for m in field_matches if m["id"] == next_id), None)
    else:
        idx = field_matches.index(now_match)
        next_match = field_matches[idx + 1] if idx + 1 < len(field_matches) else None

    seconds = None
    if next_match is not None:
        target_str = live.get("nextStartsAt")
        target = datetime.fromisoformat(target_str) if target_str else _match_dt(next_match)
        seconds = max(0, int((target - now_dt).total_seconds()))

    return {
        "field": field,
        "division": now_match["division"],
        "now": _view(now_match),
        "next": _view(next_match) if next_match else None,
        "secondsUntilNext": seconds,
        "countdown": format_countdown(seconds),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest live/tests/test_schedule_logic.py -v`
Expected: PASS — all tests green (14 cases incl. parametrized).

- [ ] **Step 5: Checkpoint — full suite**

Run: `python -m pytest live -v`
Expected: all pass. (No commit — project rule.)

---

### Task 3: Schedule importer + seed `schedule.json`

Stores the operator's markdown verbatim, converts to JSON, validates (round-robin completeness + near-duplicate team names), and seeds the live pointers. A `CORRECTIONS` map fixes the known `TurtleRabbot` typo without editing the source markdown.

**Files:**
- Create: `live/data/schedule.md` (the operator's schedule, verbatim)
- Create: `live/import_schedule.py`
- Output (generated): `live/data/schedule.json`

- [ ] **Step 1: Create `live/data/schedule.md`**

Paste the full schedule exactly as provided by the owner (all four days, three fields). It begins:

```markdown
# Thursday July 2nd
## Field A
### 08:30 | G1 | TIGERs | Ri-one
```
…through…
```markdown
# Sunday July 5th
## Field B0
### 11:00 | Grand Final | WLF | WUF
```

(Use the complete markdown block the owner pasted on 2026-06-16, unedited — including `TurtleRabbot`; the importer corrects it.)

- [ ] **Step 2: Create `live/import_schedule.py`**

```python
#!/usr/bin/env python3
"""Convert live/data/schedule.md -> live/data/schedule.json, validating as it goes.

Markdown shape:  '# <Day>'  ->  '## Field <X>'  ->  '### time | label | teamA | teamB'
Run: python live/import_schedule.py
"""
import difflib
import itertools
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "data", "schedule.md")
OUT = os.path.join(HERE, "data", "schedule.json")
YEAR = 2026
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

# Known corrections applied to team names (source markdown left untouched).
CORRECTIONS = {"TurtleRabbot": "TurtleRabbit"}


def parse_day(header):
    mm = re.search(r"(" + "|".join(MONTHS) + r")\s+(\d+)", header)
    return f"{YEAR}-{MONTHS[mm.group(1)]:02d}-{int(mm.group(2)):02d}"


def fix(name):
    return CORRECTIONS.get(name, name)


def parse(path):
    day = field = None
    out = []
    counters = defaultdict(int)
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip()
        if ln.startswith("# "):
            day = parse_day(ln[2:])
        elif ln.startswith("## "):
            field = ln[3:].strip().replace("Field ", "")
        elif ln.startswith("### "):
            t, label, a, b = [p.strip() for p in ln[4:].split("|")]
            hh, mm = t.split(":")
            time = f"{int(hh):02d}:{int(mm):02d}"
            counters[(day, field)] += 1
            n = counters[(day, field)]
            out.append({
                "id": f"{day}-{field}-{n}",
                "day": day,
                "division": "A" if field == "A" else "B",
                "field": field,
                "time": time,
                "label": label,
                "teamA": fix(a),
                "teamB": fix(b),
            })
    return out


def validate(schedule):
    groups = defaultdict(list)
    teams = set()
    for m in schedule:
        if re.fullmatch(r"G\d", m["label"]):  # pure group-stage match
            groups[(m["division"], m["label"])].append((m["teamA"], m["teamB"]))
            teams.update([m["teamA"], m["teamB"]])
    print("=== round-robin check ===")
    ok = True
    for (d, g), pairs in sorted(groups.items()):
        ts = sorted({x for p in pairs for x in p})
        expected = len(ts) * (len(ts) - 1) // 2
        seen = defaultdict(int)
        for a, b in pairs:
            seen[frozenset((a, b))] += 1
        missing = [c for c in itertools.combinations(ts, 2) if frozenset(c) not in seen]
        dups = [tuple(k) for k, v in seen.items() if v > 1]
        good = len(pairs) == expected and not missing and not dups
        ok = ok and good
        print(f"Div {d} {g}: {len(ts)} teams, {len(pairs)}/{expected} [{'OK' if good else 'CHECK'}]")
        if missing:
            print(f"   missing: {missing}")
        if dups:
            print(f"   duplicate: {dups}")
    print(f"distinct group-stage teams: {len(teams)}")
    tl = sorted(teams)
    for i, a in enumerate(tl):
        for b in tl[i + 1:]:
            if a.lower() != b.lower() and difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.85:
                print(f"   WARNING near-duplicate names: {a!r} ~ {b!r}")
                ok = False
    return ok


def seed_live(schedule):
    """currentId per field = earliest match on that field."""
    by_field = defaultdict(list)
    for m in schedule:
        by_field[m["field"]].append(m)
    live = {}
    for f, ms in by_field.items():
        ms.sort(key=lambda m: (m["day"], m["time"]))
        live[f] = {"currentId": ms[0]["id"]}
    return live


def main():
    schedule = parse(SRC)
    ok = validate(schedule)
    data = {"schedule": schedule, "live": seed_live(schedule)}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUT}: {len(schedule)} matches, fields {sorted(data['live'])}")
    print("VALIDATION:", "OK" if ok else "PROBLEMS ABOVE")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the importer**

Run: `python live/import_schedule.py`
Expected output: every group line reads `[OK]`, `distinct group-stage teams: 22`, no `near-duplicate` warnings (the `TurtleRabbot` correction merged it into `TurtleRabbit`), and `VALIDATION: OK`. A `live/data/schedule.json` is written with 58 matches and fields `['A', 'B0', 'B1']`.

- [ ] **Step 4: Spot-check the generated JSON**

Run: `python -c "import json; d=json.load(open('live/data/schedule.json')); print(d['schedule'][0]); print(d['live'])"`
Expected: first entry is the Thursday Field A G1 `TIGERs vs Ri-one` with `division: A`; `live` has a `currentId` for `A`, `B0`, `B1`.

- [ ] **Step 5: Checkpoint — full suite**

Run: `python -m pytest live -v`
Expected: all pass (importer adds no test regressions).

---

### Task 4: Flask server (`app.py`) with hot-reload + routes

**Files:**
- Create: `live/app.py`
- Test: `live/tests/test_app.py`

- [ ] **Step 1: Write the failing route tests**

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest live/tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'` (or cannot import `create_app`).

- [ ] **Step 3: Write the implementation**

```python
# live/app.py
"""Flask server: serves per-field now/next/countdown JSON for OBS obs-urlsource.

Run: PORT=8000 python live/app.py   (binds 0.0.0.0 so other PCs reach it over LAN)
"""
import json
import os
from datetime import datetime

from flask import Flask, jsonify

from schedule_logic import resolve

DEFAULT_DATA = os.path.join(os.path.dirname(__file__), "data", "schedule.json")


def create_app(data_path=DEFAULT_DATA):
    app = Flask(__name__)
    cache = {"mtime": None, "data": None}

    def load_data():
        """Re-read schedule.json only when its mtime changes (hot-reload)."""
        mtime = os.path.getmtime(data_path)
        if cache["mtime"] != mtime:
            with open(data_path, encoding="utf-8") as fh:
                cache["data"] = json.load(fh)
            cache["mtime"] = mtime
        return cache["data"]

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/field/<field>")
    def field(field):
        try:
            return jsonify(resolve(load_data(), field, datetime.now()))
        except ValueError as exc:
            msg = str(exc)
            code = 404 if msg.startswith("unknown field") else 422
            return jsonify(error=msg), code

    return app


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    create_app().run(host=host, port=port)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest live/tests/test_app.py -v`
Expected: PASS — all four route tests green (incl. the hot-reload 422 case).

- [ ] **Step 5: Manual smoke test against the real seeded data**

Run (terminal A): `PORT=8000 python live/app.py`
Run (terminal B): `curl -s localhost:8000/field/A | python -m json.tool` then `curl -s localhost:8000/field/B0` and `curl -s localhost:8000/field/B1`
Expected: each returns a JSON body with `now`, `next`, `secondsUntilNext`, `countdown`, `division`. Edit `live/data/schedule.json` (bump `live.A.currentId` to the next match's id), re-run the curl — the `now`/`next` change **without restarting** the server. Stop the server (Ctrl-C).

- [ ] **Step 6: Checkpoint — full suite**

Run: `python -m pytest live -v`
Expected: all pass.

---

### Task 5: `live/README.md` — run + per-PC OBS setup checklist

**Files:**
- Create: `live/README.md`

- [ ] **Step 1: Write `live/README.md`**

````markdown
# Live match data server

Serves per-field "now / next / countdown" JSON for the RoboCup 2026 SSL broadcast.
OBS pulls it with the **obs-urlsource** plugin and renders it as native text. You drive
it by editing one file — no clock guessing, no scene automation.

## Run (on ONE machine — the others reach it over the LAN)

```bash
pip install -r requirements.txt
python import_schedule.py                # (re)build data/schedule.json from data/schedule.md
PORT=8000 python app.py                  # binds 0.0.0.0:8000
```

Endpoints: `GET /field/A`, `/field/B0`, `/field/B1`, `/health`.

## Driving it during the stream

Edit `data/schedule.json` → `live.<field>.currentId` to the id of the match now on that
field; save. The server hot-reloads on save (no restart). Optional per-field overrides:
- `nextId` — force which match counts as "next".
- `nextStartsAt` — explicit ISO time for the countdown (e.g. `"2026-07-02T10:15"`) when a
  match is running late.

Divisions: Field A = Division A; Fields B0 + B1 = Division B. Group labels and playoff
codes repeat across divisions — that's expected; matches are keyed by field.

## Per-PC OBS setup checklist (for distributing the scene collection)

The Scene Collection export carries the urlsource URLs, text styling, and image/media
sources, but each target PC must have:

1. **obs-urlsource plugin installed** (https://github.com/royshil/obs-urlsource) — the
   collection references it; without it those text sources show as missing.
2. **Asset files at the SAME absolute path** on every PC (OBS stores absolute paths):
   keep `next-match.png`, `breathing-background.mp4`, `standby.mp4` in an identical folder
   (e.g. `C:\robocup\assets\`). Install the **brand font** on every PC or text falls back.
3. The urlsource URLs point at the **server's fixed LAN IP/hostname**, NOT `localhost`
   (e.g. `http://192.168.1.50:8000/field/A`) — so every PC pulls from the one shared file.

### Wiring one field's text in OBS

Add an **obs-urlsource** source → URL `http://<server>:8000/field/A` → refresh every
1–2 s → output type **Text**, extract a JSON pointer (e.g. `now.matchup`, `next.matchup`,
or `countdown`) → style with the brand font. Repeat per field / per string you want; place
over the `NextMatch` slot / lower-third. The plugin's output template can also combine
fields, e.g. `NEXT: {next.matchup} — {countdown}`.
````

- [ ] **Step 2: Verify it renders**

Run: `python -c "print(open('live/README.md').read()[:200])"`
Expected: prints the README header — confirms the file exists and is readable.

- [ ] **Step 3: Checkpoint — full suite**

Run: `python -m pytest live -v`
Expected: all pass.

---

## Final verification

- [ ] `python -m pytest live -v` — all tests pass.
- [ ] `python live/import_schedule.py` — `VALIDATION: OK`, 22 teams, all groups `[OK]`.
- [ ] Server boots; `curl localhost:8000/field/A|B0|B1` return valid payloads; editing
      `schedule.json` hot-reloads without restart.
- [ ] `live/README.md` documents run steps + the 3-point per-PC checklist.

---

## REVISION 2026-06-16b — obs-websocket delivery (supersedes the Flask delivery)

Per the spec revision: drop the Flask HTTP server + obs-urlsource. Each machine runs a local
`obs_push.py` that pushes match text into its own local OBS via the built-in obs-websocket.
**Reuses `schedule_logic.resolve()` unchanged.** Tasks 1-3 stand; this replaces Task 4's
Flask app and revises Task 5's README.

### Task R1: replace the Flask app with an obs-websocket pusher

**Files:**
- Delete: `live/app.py`, `live/tests/test_app.py`
- Modify: `live/requirements.txt` (drop `flask`, add `obsws-python`)
- Create: `live/obs_push.py`
- Test: `live/tests/test_obs_push.py`

- [ ] **Step 1: Update `live/requirements.txt`**

```
obsws-python>=1.6
pytest>=8.0
```

Then `pip install -r live/requirements.txt`. Delete `live/app.py`
and `live/tests/test_app.py`.

- [ ] **Step 2: Write the failing test** `live/tests/test_obs_push.py`

```python
from datetime import datetime

from obs_push import field_updates

DATA = {
    "schedule": [
        {"id": "d1-A-1", "day": "2026-07-02", "division": "A", "field": "A",
         "time": "08:30", "label": "G1", "teamA": "TIGERs", "teamB": "Ri-one"},
        {"id": "d1-A-2", "day": "2026-07-02", "division": "A", "field": "A",
         "time": "10:00", "label": "G2", "teamA": "ZJUNLict", "teamB": "LUHBots"},
    ],
    "live": {"A": {"currentId": "d1-A-1"}},
}


def test_field_updates_maps_source_names_to_text():
    u = field_updates(DATA, "A", datetime(2026, 7, 2, 9, 0))
    assert u == {
        "match_A_now": "TIGERs vs Ri-one",
        "match_A_next": "ZJUNLict vs LUHBots",
        "match_A_countdown": "1:00:00",
    }


def test_field_updates_last_match_blanks_next_and_countdown():
    data = {**DATA, "live": {"A": {"currentId": "d1-A-2"}}}
    u = field_updates(data, "A", datetime(2026, 7, 2, 11, 0))
    assert u["match_A_now"] == "ZJUNLict vs LUHBots"
    assert u["match_A_next"] == ""
    assert u["match_A_countdown"] == ""


def test_field_updates_unconfigured_field_returns_empty():
    # a field with no matches / not configured must NOT raise — just yield nothing
    assert field_updates(DATA, "B1", datetime(2026, 7, 2, 9, 0)) == {}
```

- [ ] **Step 3: Run it — expect FAIL** (`No module named 'obs_push'`).

Run: `python -m pytest live/tests/test_obs_push.py -v`

- [ ] **Step 4: Write `live/obs_push.py`**

```python
"""Push per-field match text into the LOCAL OBS via obs-websocket (OBS 28+ built-in).

Each machine runs its own copy against its own OBS. Reuses the tested schedule_logic.
Run: OBS_WS_PASSWORD=yourpw python live/obs_push.py
Env: OBS_WS_HOST (localhost), OBS_WS_PORT (4455), OBS_WS_PASSWORD (""),
     PUSH_INTERVAL (1.0 seconds).
The operator creates native Text sources named match_<field>_{now,next,countdown};
the pusher updates any that exist and skips the rest.
"""
import json
import os
import time
from datetime import datetime

from schedule_logic import resolve

FIELDS = ["A", "B0", "B1"]
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "schedule.json")


def field_updates(data, field, now_dt):
    """Map a field's resolved state to {obs_source_name: text}. Returns {} (no raise)
    if the field isn't configured/has no current match."""
    try:
        r = resolve(data, field, now_dt)
    except ValueError:
        return {}
    return {
        f"match_{field}_now": r["now"]["matchup"],
        f"match_{field}_next": r["next"]["matchup"] if r["next"] else "",
        f"match_{field}_countdown": r["countdown"] or "",
    }


def _make_loader(path):
    cache = {"mtime": None, "data": None}

    def load():
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return cache["data"]
        if cache["mtime"] != mtime:
            try:
                with open(path, encoding="utf-8") as fh:
                    cache["data"] = json.load(fh)
                cache["mtime"] = mtime
            except (OSError, json.JSONDecodeError):
                pass  # keep last good; retry next tick
        return cache["data"]

    return load


def run():
    import obsws_python as obsws

    host = os.environ.get("OBS_WS_HOST", "localhost")
    port = int(os.environ.get("OBS_WS_PORT", "4455"))
    password = os.environ.get("OBS_WS_PASSWORD", "")
    interval = float(os.environ.get("PUSH_INTERVAL", "1.0"))

    load = _make_loader(DATA_PATH)
    client = None
    sent = {}
    while True:
        try:
            if client is None:
                client = obsws.ReqClient(host=host, port=port, password=password, timeout=3)
                sent = {}  # force a full re-push after (re)connect
                print(f"connected to OBS at {host}:{port}")
            data = load()
        except Exception as exc:  # connection failed — back off and retry
            print(f"OBS connect failed ({exc}); retrying...")
            client = None
            time.sleep(2)
            continue

        if data is not None:
            now = datetime.now()
            for field in FIELDS:
                for name, text in field_updates(data, field, now).items():
                    if sent.get(name) == text:
                        continue
                    try:
                        client.set_input_settings(name, {"text": text}, overlay=True)
                        sent[name] = text
                    except Exception as exc:  # missing source, or dropped connection
                        msg = str(exc).lower()
                        if "not found" in msg or "no source" in msg:
                            continue  # source simply doesn't exist in this scene; skip
                        print(f"push failed for {name} ({exc}); reconnecting")
                        client = None
                        break
                if client is None:
                    break
        time.sleep(interval)


if __name__ == "__main__":
    run()
```

- [ ] **Step 5: Run the tests — expect PASS**

Run: `python -m pytest live -v`
Expected: the 3 new `test_obs_push.py` tests pass alongside the 17 `schedule_logic` tests (20 total; the 4 Flask tests are gone). Note `field_updates` is the pure tested layer; `run()`'s websocket loop is verified manually against a real OBS.

- [ ] **Step 6: Checkpoint — full suite** `python -m pytest live -v`. All pass.

### Task R2: update `live/README.md` for the websocket model

- [ ] **Step 1:** Replace the run/usage and per-PC sections of `live/README.md` so they describe:
  - Run: `OBS_WS_PASSWORD=… python live/obs_push.py` (env vars listed above); `python import_schedule.py` to rebuild the data.
  - Drive it: edit `data/schedule.json` → `live.<field>.currentId`; the pusher hot-reloads and pushes within one tick.
  - Per-PC setup (no plugin): install stock OBS → **enable Tools ▸ WebSocket Server Settings** + set a password → create native **Text (GDI+/FreeType)** sources named `match_<field>_{now,next,countdown}` (field A/B0/B1) and style them → import the scene collection → copy `live/` + `schedule.json` → run `obs_push.py` with `OBS_WS_PASSWORD`.
  - Note: each machine runs its own pusher against its own localhost OBS; `schedule.json` is copied per machine for now (USB/manual).
- [ ] **Step 2:** `python -m pytest live -v` still passes (docs change only).

### Final (revised)
- [ ] `python -m pytest live -v` — `schedule_logic` (17) + `obs_push` (3) pass; no Flask remnants.
- [ ] `live/` contains `obs_push.py` (not `app.py`); `requirements.txt` lists `obsws-python`, not `flask`.
- [ ] Manual smoke test against a real OBS (operator): enable websocket, add a `match_A_now`
      Text source, run `obs_push.py`, confirm the text appears and updates when `currentId` changes.
