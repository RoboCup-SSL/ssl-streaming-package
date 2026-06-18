# Live Match Text via OBS Websocket — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive OBS native text (team names, score, match stage, next-up/countdown) from the SSL Game Controller feed, event-driven, for a single field — with no manual typing.

**Architecture:** Concern-based `uv` workspace under `services/`: `data_structures` (domain + proto), `data_access` (GC multicast, fake source, OBS websocket, schedule file), `data_processing` (decode, format, schedule resolve), `configuration` (one `field.toml` → `FieldConfig`), and a thin `obs-live-data` app running one asyncio loop. Dependencies point only "down" toward `data_structures`.

**Tech Stack:** Python 3.12+, `uv` workspace, `protobuf`, `simpleobsws` (obs-websocket v5), `tomllib` (stdlib), `pytest` + `pytest-asyncio`.

## Global Constraints

- Python `>=3.12`; `uv` for all dependency management and running (`uv run ...`). No `--index-url`/registry flags (environment is pre-configured).
- Event-driven, single asyncio loop, one process. No threads, no multi-process supervision.
- OBS control is **push** over obs-websocket v5 via `simpleobsws` only. No `obs-urlsource`, no HTTP server.
- One `obs-live-data` per field; field identity comes from config, never a parameter/route.
- Small single-purpose files, dataclasses, full type hints, readable names, comments for *why* not *what*.
- No real network or real OBS in automated tests; use `FakeRefereeSource` and a recording stub OBS client. The multicast loopback check is manual, not in CI.
- Dependency direction: `data_access` and `data_processing` depend only on `data_structures`; `configuration` aggregates each lib's config dataclass; the app depends on all.

---

### Task 1: uv workspace + `data_structures` domain & enums

**Files:**
- Create: `services/pyproject.toml` (workspace root)
- Create: `services/data_structures/pyproject.toml`
- Create: `services/data_structures/data_structures/__init__.py`
- Create: `services/data_structures/data_structures/enums.py`
- Create: `services/data_structures/data_structures/domain.py`
- Create: `services/data_structures/data_structures/sources.py`
- Test: `services/data_structures/tests/test_domain.py`

**Interfaces:**
- Produces: `Stage`, `Command` (`IntEnum`); `Team(name:str, score:int, yellow_cards:int)`; `MatchState(stage:Stage, command:Command, blue:Team, yellow:Team)`; `RefereeSource` (Protocol with `__aiter__() -> AsyncIterator[MatchState]`).

- [ ] **Step 1: Write the failing test**

```python
# services/data_structures/tests/test_domain.py
from data_structures.domain import Team, MatchState
from data_structures.enums import Stage, Command


def test_matchstate_holds_teams_and_phase():
    state = MatchState(
        stage=Stage.NORMAL_FIRST_HALF,
        command=Command.NORMAL_START,
        blue=Team(name="ER-Force", score=1, yellow_cards=0),
        yellow=Team(name="TIGERs", score=2, yellow_cards=1),
    )
    assert state.blue.name == "ER-Force"
    assert state.yellow.score == 2
    assert state.stage is Stage.NORMAL_FIRST_HALF
    assert int(Command.GOAL_BLUE) == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_structures && uv run pytest tests/test_domain.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```toml
# services/pyproject.toml
[tool.uv.workspace]
members = ["configuration", "data_structures", "data_access", "data_processing", "obs-live-data"]
```

```toml
# services/data_structures/pyproject.toml
[project]
name = "data-structures"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=8.0"]
```

```python
# services/data_structures/data_structures/enums.py
from enum import IntEnum


class Stage(IntEnum):
    NORMAL_FIRST_HALF_PRE = 0
    NORMAL_FIRST_HALF = 1
    NORMAL_HALF_TIME = 2
    NORMAL_SECOND_HALF_PRE = 3
    NORMAL_SECOND_HALF = 4
    EXTRA_TIME_BREAK = 5
    EXTRA_FIRST_HALF_PRE = 6
    EXTRA_FIRST_HALF = 7
    EXTRA_HALF_TIME = 8
    EXTRA_SECOND_HALF_PRE = 9
    EXTRA_SECOND_HALF = 10
    PENALTY_SHOOTOUT_BREAK = 11
    PENALTY_SHOOTOUT = 12
    POST_GAME = 13


class Command(IntEnum):
    HALT = 0
    STOP = 1
    NORMAL_START = 2
    FORCE_START = 3
    PREPARE_KICKOFF_YELLOW = 4
    PREPARE_KICKOFF_BLUE = 5
    PREPARE_PENALTY_YELLOW = 6
    PREPARE_PENALTY_BLUE = 7
    DIRECT_FREE_YELLOW = 8
    DIRECT_FREE_BLUE = 9
    INDIRECT_FREE_YELLOW = 10
    INDIRECT_FREE_BLUE = 11
    TIMEOUT_YELLOW = 12
    TIMEOUT_BLUE = 13
    GOAL_YELLOW = 14
    GOAL_BLUE = 15
    BALL_PLACEMENT_YELLOW = 16
    BALL_PLACEMENT_BLUE = 17
```

```python
# services/data_structures/data_structures/domain.py
from dataclasses import dataclass

from data_structures.enums import Command, Stage


@dataclass(frozen=True)
class Team:
    name: str
    score: int
    yellow_cards: int


@dataclass(frozen=True)
class MatchState:
    stage: Stage
    command: Command
    blue: Team
    yellow: Team
```

```python
# services/data_structures/data_structures/sources.py
from typing import AsyncIterator, Protocol

from data_structures.domain import MatchState


class RefereeSource(Protocol):
    def __aiter__(self) -> AsyncIterator[MatchState]: ...
```

```python
# services/data_structures/data_structures/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_structures && uv run pytest tests/test_domain.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/pyproject.toml services/data_structures
git commit -m "feat(data_structures): domain types, enums, RefereeSource protocol"
```

---

### Task 2: Minimal Referee proto + generated `_pb2`

**Files:**
- Create: `services/data_structures/data_structures/proto/ssl_gc_referee.proto`
- Create: `services/data_structures/data_structures/proto/regen.sh`
- Create: `services/data_structures/data_structures/proto/__init__.py`
- Generated: `services/data_structures/data_structures/proto/ssl_gc_referee_pb2.py`
- Modify: `services/data_structures/pyproject.toml` (add `protobuf`, dev `grpcio-tools`)
- Test: `services/data_structures/tests/test_proto.py`

**Interfaces:**
- Produces: `data_structures.proto.ssl_gc_referee_pb2.Referee` with fields `stage`, `command`, `command_counter`, `command_timestamp`, `yellow`, `blue` (each `TeamInfo` with `name`, `score`, `yellow_cards`).

> Field numbers and enum values copied verbatim from `_resources/ssl-game-controller/proto/state/ssl_gc_referee_message.proto`. proto3 is wire-compatible with the GC's proto2 output by field number.

- [ ] **Step 1: Write the failing test**

```python
# services/data_structures/tests/test_proto.py
from data_structures.proto import ssl_gc_referee_pb2 as pb


def test_referee_roundtrip():
    ref = pb.Referee(stage=1, command=2, command_counter=7, command_timestamp=123)
    ref.yellow.name = "TIGERs"
    ref.yellow.score = 2
    ref.blue.name = "ER-Force"
    ref.blue.score = 1
    parsed = pb.Referee()
    parsed.ParseFromString(ref.SerializeToString())
    assert parsed.blue.name == "ER-Force"
    assert parsed.yellow.score == 2
    assert parsed.command == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_structures && uv run pytest tests/test_proto.py -v`
Expected: FAIL (no `ssl_gc_referee_pb2`).

- [ ] **Step 3: Write minimal implementation**

```protobuf
// services/data_structures/data_structures/proto/ssl_gc_referee.proto
// Minimal wire-compatible subset of the SSL Game Controller Referee message.
// Field numbers + enum values copied from ssl-game-controller
// proto/state/ssl_gc_referee_message.proto. proto3 parses the GC's proto2 wire bytes.
syntax = "proto3";

message Referee {
  uint64 packet_timestamp = 1;

  enum Stage {
    NORMAL_FIRST_HALF_PRE = 0;
    NORMAL_FIRST_HALF = 1;
    NORMAL_HALF_TIME = 2;
    NORMAL_SECOND_HALF_PRE = 3;
    NORMAL_SECOND_HALF = 4;
    EXTRA_TIME_BREAK = 5;
    EXTRA_FIRST_HALF_PRE = 6;
    EXTRA_FIRST_HALF = 7;
    EXTRA_HALF_TIME = 8;
    EXTRA_SECOND_HALF_PRE = 9;
    EXTRA_SECOND_HALF = 10;
    PENALTY_SHOOTOUT_BREAK = 11;
    PENALTY_SHOOTOUT = 12;
    POST_GAME = 13;
  }
  Stage stage = 2;
  sint64 stage_time_left = 3;

  enum Command {
    HALT = 0;
    STOP = 1;
    NORMAL_START = 2;
    FORCE_START = 3;
    PREPARE_KICKOFF_YELLOW = 4;
    PREPARE_KICKOFF_BLUE = 5;
    PREPARE_PENALTY_YELLOW = 6;
    PREPARE_PENALTY_BLUE = 7;
    DIRECT_FREE_YELLOW = 8;
    DIRECT_FREE_BLUE = 9;
    INDIRECT_FREE_YELLOW = 10;
    INDIRECT_FREE_BLUE = 11;
    TIMEOUT_YELLOW = 12;
    TIMEOUT_BLUE = 13;
    GOAL_YELLOW = 14;
    GOAL_BLUE = 15;
    BALL_PLACEMENT_YELLOW = 16;
    BALL_PLACEMENT_BLUE = 17;
  }
  Command command = 4;
  uint32 command_counter = 5;
  uint64 command_timestamp = 6;

  message TeamInfo {
    string name = 1;
    uint32 score = 2;
    uint32 red_cards = 3;
    repeated uint32 yellow_card_times = 4;
    uint32 yellow_cards = 5;
  }
  TeamInfo yellow = 7;
  TeamInfo blue = 8;
}
```

```bash
# services/data_structures/data_structures/proto/regen.sh
#!/usr/bin/env bash
# Regenerate the protobuf bindings. Run from the proto/ dir: ./regen.sh
set -euo pipefail
cd "$(dirname "$0")"
uv run python -m grpc_tools.protoc -I. --python_out=. ssl_gc_referee.proto
```

```toml
# add to services/data_structures/pyproject.toml [project].dependencies
dependencies = ["protobuf>=5.0"]
# add to [dependency-groups].dev
dev = ["pytest>=8.0", "grpcio-tools>=1.60"]
```

Create `proto/__init__.py` (empty). Then generate:

Run: `cd services/data_structures/data_structures/proto && chmod +x regen.sh && ./regen.sh`
Expected: writes `ssl_gc_referee_pb2.py`.

> If `grpcio-tools` is unavailable in this environment, ask the operator to run `regen.sh` (matches the "installs run manually" policy), then continue.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_structures && uv run pytest tests/test_proto.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_structures
git commit -m "feat(data_structures): minimal Referee proto + generated bindings"
```

---

### Task 3: `data_processing.decode`

**Files:**
- Create: `services/data_processing/pyproject.toml`
- Create: `services/data_processing/data_processing/__init__.py`
- Create: `services/data_processing/data_processing/decode.py`
- Test: `services/data_processing/tests/test_decode.py`

**Interfaces:**
- Consumes: `ssl_gc_referee_pb2.Referee`; `MatchState`, `Team`, `Stage`, `Command`.
- Produces: `decode_referee(payload: bytes) -> MatchState`.

- [ ] **Step 1: Write the failing test**

```python
# services/data_processing/tests/test_decode.py
from data_processing.decode import decode_referee
from data_structures.enums import Command, Stage
from data_structures.proto import ssl_gc_referee_pb2 as pb


def _payload():
    ref = pb.Referee(stage=4, command=15, command_counter=3, command_timestamp=9)
    ref.blue.name, ref.blue.score, ref.blue.yellow_cards = "ER-Force", 1, 0
    ref.yellow.name, ref.yellow.score, ref.yellow.yellow_cards = "TIGERs", 2, 1
    return ref.SerializeToString()


def test_decode_referee_maps_fields():
    state = decode_referee(_payload())
    assert state.stage is Stage.NORMAL_SECOND_HALF
    assert state.command is Command.GOAL_BLUE
    assert state.blue.name == "ER-Force" and state.blue.score == 1
    assert state.yellow.name == "TIGERs" and state.yellow.yellow_cards == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_processing && uv run pytest tests/test_decode.py -v`
Expected: FAIL (no `decode_referee`).

- [ ] **Step 3: Write minimal implementation**

```toml
# services/data_processing/pyproject.toml
[project]
name = "data-processing"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["data-structures"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.uv.sources]
data-structures = { workspace = true }
```

```python
# services/data_processing/data_processing/decode.py
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from data_structures.proto import ssl_gc_referee_pb2 as pb


def _team(info: pb.Referee.TeamInfo) -> Team:
    return Team(name=info.name, score=info.score, yellow_cards=info.yellow_cards)


def decode_referee(payload: bytes) -> MatchState:
    ref = pb.Referee()
    ref.ParseFromString(payload)
    return MatchState(
        stage=Stage(ref.stage),
        command=Command(ref.command),
        blue=_team(ref.blue),
        yellow=_team(ref.yellow),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_processing && uv run pytest tests/test_decode.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_processing
git commit -m "feat(data_processing): decode Referee bytes to MatchState"
```

---

### Task 4: `data_processing.schedule` (single-field resolve)

**Files:**
- Create: `services/data_processing/data_processing/schedule.py`
- Test: `services/data_processing/tests/test_schedule.py`
- Reference (carry-over source, to be deleted in Task 11): `services/obs-live-data/schedule_logic.py`

**Interfaces:**
- Produces: `resolve(data: dict, field: str, now_dt: datetime) -> dict`; `format_countdown(seconds: int | None) -> str | None`; `ScheduleConfig(path: str)`.

- [ ] **Step 1: Write the failing test**

```python
# services/data_processing/tests/test_schedule.py
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
    assert out["countdown"] == "60:00"


def test_format_countdown_clamps_and_formats():
    assert format_countdown(None) is None
    assert format_countdown(-5) == "0:00"
    assert format_countdown(3661) == "1:01:01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_processing && uv run pytest tests/test_schedule.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```python
# services/data_processing/data_processing/schedule.py
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScheduleConfig:
    path: str


def _match_dt(m: dict) -> datetime:
    return datetime.strptime(f'{m["day"]} {m["time"]}', "%Y-%m-%d %H:%M")


def _view(m: dict) -> dict:
    return {
        "label": m["label"],
        "teamA": m["teamA"],
        "teamB": m["teamB"],
        "time": m["time"],
        "matchup": f'{m["teamA"]} vs {m["teamB"]}',
    }


def format_countdown(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def resolve(data: dict, field: str, now_dt: datetime) -> dict:
    field_matches = sorted(
        (m for m in data["schedule"] if m["field"] == field), key=_match_dt
    )
    if not field_matches:
        raise ValueError(f"unknown field: {field!r}")

    live = data.get("live", {}).get(field, {})
    current_id = live.get("currentId")
    if current_id is None:
        raise ValueError(f"no currentId configured for field {field!r}")
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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_processing && uv run pytest tests/test_schedule.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_processing
git commit -m "feat(data_processing): single-field schedule resolve + countdown"
```

---

### Task 5: `data_processing.format`

**Files:**
- Create: `services/data_processing/data_processing/format.py`
- Test: `services/data_processing/tests/test_format.py`

**Interfaces:**
- Consumes: `MatchState`, `Stage`; the `sources` name-map dict (logical key → OBS source name); a schedule view dict (or `None`).
- Produces: `format_updates(state: MatchState | None, schedule_view: dict | None, sources: dict[str, str]) -> dict[str, str]` (OBS source name → text). Keys absent from `sources` are skipped. Also `stage_label(stage: Stage) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# services/data_processing/tests/test_format.py
from data_processing.format import format_updates, stage_label
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage

SOURCES = {
    "blue_name": "txt_blue", "blue_score": "txt_blue_score",
    "yellow_name": "txt_yellow", "yellow_score": "txt_yellow_score",
    "stage": "txt_stage", "next_match": "txt_next", "countdown": "txt_cd",
}


def _state():
    return MatchState(
        stage=Stage.NORMAL_FIRST_HALF, command=Command.NORMAL_START,
        blue=Team("ER-Force", 1, 0), yellow=Team("TIGERs", 2, 0),
    )


def test_stage_label_is_human_readable():
    assert stage_label(Stage.NORMAL_HALF_TIME) == "Half Time"


def test_format_updates_maps_to_source_names():
    view = {"next": {"matchup": "A vs B"}, "countdown": "5:00"}
    out = format_updates(_state(), view, SOURCES)
    assert out["txt_blue"] == "ER-Force"
    assert out["txt_blue_score"] == "1"
    assert out["txt_yellow_score"] == "2"
    assert out["txt_stage"] == "First Half"
    assert out["txt_next"] == "A vs B"
    assert out["txt_cd"] == "5:00"


def test_format_updates_skips_unmapped_keys():
    out = format_updates(_state(), None, {"blue_name": "txt_blue"})
    assert out == {"txt_blue": "ER-Force"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_processing && uv run pytest tests/test_format.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```python
# services/data_processing/data_processing/format.py
from data_structures.domain import MatchState
from data_structures.enums import Stage

_STAGE_LABELS = {
    Stage.NORMAL_FIRST_HALF_PRE: "Pre First Half",
    Stage.NORMAL_FIRST_HALF: "First Half",
    Stage.NORMAL_HALF_TIME: "Half Time",
    Stage.NORMAL_SECOND_HALF_PRE: "Pre Second Half",
    Stage.NORMAL_SECOND_HALF: "Second Half",
    Stage.EXTRA_TIME_BREAK: "Extra Time Break",
    Stage.EXTRA_FIRST_HALF_PRE: "Pre Extra First Half",
    Stage.EXTRA_FIRST_HALF: "Extra First Half",
    Stage.EXTRA_HALF_TIME: "Extra Half Time",
    Stage.EXTRA_SECOND_HALF_PRE: "Pre Extra Second Half",
    Stage.EXTRA_SECOND_HALF: "Extra Second Half",
    Stage.PENALTY_SHOOTOUT_BREAK: "Penalty Shootout Break",
    Stage.PENALTY_SHOOTOUT: "Penalty Shootout",
    Stage.POST_GAME: "Post Game",
}


def stage_label(stage: Stage) -> str:
    return _STAGE_LABELS[stage]


def format_updates(
    state: MatchState | None,
    schedule_view: dict | None,
    sources: dict[str, str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    if state is not None:
        values["blue_name"] = state.blue.name
        values["blue_score"] = str(state.blue.score)
        values["yellow_name"] = state.yellow.name
        values["yellow_score"] = str(state.yellow.score)
        values["stage"] = stage_label(state.stage)
    if schedule_view is not None:
        nxt = schedule_view.get("next")
        if nxt is not None:
            values["next_match"] = nxt["matchup"]
        if schedule_view.get("countdown") is not None:
            values["countdown"] = schedule_view["countdown"]
    return {sources[key]: text for key, text in values.items() if key in sources}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_processing && uv run pytest tests/test_format.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_processing
git commit -m "feat(data_processing): format MatchState + schedule into OBS text updates"
```

---

### Task 6: `data_access` config + OBS websocket client

**Files:**
- Create: `services/data_access/pyproject.toml`
- Create: `services/data_access/data_access/__init__.py`
- Create: `services/data_access/data_access/config.py`
- Create: `services/data_access/data_access/obs.py`
- Test: `services/data_access/tests/test_obs.py`

**Interfaces:**
- Produces: `GameControllerConfig(address:str, port:int)`; `ObsConfig(url:str, password:str, sources:dict[str,str], text_field:str="text")`; `ObsText(client, text_field="text")` with `async set_text(source_name:str, value:str)`.

- [ ] **Step 1: Write the failing test**

```python
# services/data_access/tests/test_obs.py
import pytest

from data_access.obs import ObsText


class RecordingClient:
    def __init__(self):
        self.calls = []

    async def call(self, request):
        self.calls.append((request.requestType, request.requestData))


@pytest.mark.asyncio
async def test_set_text_issues_setinputsettings():
    client = RecordingClient()
    obs = ObsText(client, text_field="text")
    await obs.set_text("txt_blue", "ER-Force")
    assert client.calls == [
        ("SetInputSettings",
         {"inputName": "txt_blue", "inputSettings": {"text": "ER-Force"}}),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_access && uv run pytest tests/test_obs.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```toml
# services/data_access/pyproject.toml
[project]
name = "data-access"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["data-structures", "simpleobsws>=1.4.3"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.uv.sources]
data-structures = { workspace = true }
```

```python
# services/data_access/data_access/config.py
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GameControllerConfig:
    address: str
    port: int


@dataclass(frozen=True)
class ObsConfig:
    url: str
    password: str
    sources: dict[str, str] = field(default_factory=dict)
    text_field: str = "text"
```

```python
# services/data_access/data_access/obs.py
import simpleobsws


class ObsText:
    """Sets text on named OBS sources over obs-websocket. The simpleobsws client
    is injected so it can be stubbed in tests."""

    def __init__(self, client, text_field: str = "text") -> None:
        self._client = client
        self._text_field = text_field

    async def set_text(self, source_name: str, value: str) -> None:
        request = simpleobsws.Request(
            "SetInputSettings",
            {"inputName": source_name, "inputSettings": {self._text_field: value}},
        )
        await self._client.call(request)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_access && uv run pytest tests/test_obs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_access
git commit -m "feat(data_access): config dataclasses + OBS text client"
```

---

### Task 7: `data_access.fake` (FakeRefereeSource)

**Files:**
- Create: `services/data_access/data_access/fake.py`
- Test: `services/data_access/tests/test_fake.py`

**Interfaces:**
- Produces: `FakeRefereeSource(steps: list[tuple[float, MatchState]])` implementing `RefereeSource` — `async for state in source` yields each `MatchState` after its delay (seconds).

- [ ] **Step 1: Write the failing test**

```python
# services/data_access/tests/test_fake.py
from data_access.fake import FakeRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


def _state(score):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team("B", score, 0), Team("Y", 0, 0))


async def test_fake_source_yields_states_in_order():
    src = FakeRefereeSource([(0.0, _state(0)), (0.0, _state(1))])
    seen = [s.blue.score async for s in src]
    assert seen == [0, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_access && uv run pytest tests/test_fake.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```python
# services/data_access/data_access/fake.py
import asyncio
from typing import AsyncIterator

from data_structures.domain import MatchState


class FakeRefereeSource:
    """In-process RefereeSource for tests/dev. Emits a scripted sequence with
    optional per-step delays (seconds). Sends nothing on the network."""

    def __init__(self, steps: list[tuple[float, MatchState]]) -> None:
        self._steps = steps

    async def __aiter__(self) -> AsyncIterator[MatchState]:
        for delay, state in self._steps:
            if delay:
                await asyncio.sleep(delay)
            yield state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_access && uv run pytest tests/test_fake.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_access
git commit -m "feat(data_access): in-process FakeRefereeSource"
```

---

### Task 8: `data_access.gc` (MulticastRefereeSource)

**Files:**
- Create: `services/data_access/data_access/gc.py`
- Test: `services/data_access/tests/test_gc.py`

**Interfaces:**
- Consumes: `GameControllerConfig`; an injected `decode: Callable[[bytes], MatchState]`.
- Produces: `MulticastRefereeSource(config, decode)` implementing `RefereeSource`; `async start()` joins the multicast group; `_handle(payload: bytes)` decodes one datagram onto the internal queue (skips on decode error).

- [ ] **Step 1: Write the failing test**

```python
# services/data_access/tests/test_gc.py
import asyncio

from data_access.config import GameControllerConfig
from data_access.gc import MulticastRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


def _decode_ok(payload: bytes) -> MatchState:
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team("B", payload[0], 0), Team("Y", 0, 0))


async def test_handle_decodes_and_yields():
    src = MulticastRefereeSource(GameControllerConfig("224.5.23.1", 10003), _decode_ok)
    src._handle(b"\x05")
    state = await asyncio.wait_for(src._queue.get(), timeout=1)
    assert state.blue.score == 5


async def test_handle_skips_on_decode_error():
    def boom(_):
        raise ValueError("bad")

    src = MulticastRefereeSource(GameControllerConfig("224.5.23.1", 10003), boom)
    src._handle(b"\x00")
    assert src._queue.empty()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_access && uv run pytest tests/test_gc.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```python
# services/data_access/data_access/gc.py
import asyncio
import logging
import socket
import struct
from typing import AsyncIterator, Callable

from data_access.config import GameControllerConfig
from data_structures.domain import MatchState

log = logging.getLogger(__name__)

Decode = Callable[[bytes], MatchState]


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, handle: Callable[[bytes], None]) -> None:
        self._handle = handle

    def datagram_received(self, data: bytes, addr) -> None:
        self._handle(data)


class MulticastRefereeSource:
    """RefereeSource backed by the GC multicast feed. `decode` is injected so this
    module depends only on data_structures."""

    def __init__(self, config: GameControllerConfig, decode: Decode) -> None:
        self._config = config
        self._decode = decode
        self._queue: asyncio.Queue[MatchState] = asyncio.Queue()
        self._transport: asyncio.BaseTransport | None = None

    def _handle(self, payload: bytes) -> None:
        try:
            state = self._decode(payload)
        except Exception:
            log.warning("skipping undecodable referee datagram", exc_info=True)
            return
        self._queue.put_nowait(state)

    async def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self._config.port))
        membership = struct.pack(
            "4sl", socket.inet_aton(self._config.address), socket.INADDR_ANY
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        sock.setblocking(False)
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _Protocol(self._handle), sock=sock
        )

    async def __aiter__(self) -> AsyncIterator[MatchState]:
        while True:
            yield await self._queue.get()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_access && uv run pytest tests/test_gc.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_access
git commit -m "feat(data_access): multicast RefereeSource with injected decode"
```

---

### Task 9: `data_access.schedule` (file load + hot-reload)

**Files:**
- Create: `services/data_access/data_access/schedule.py`
- Test: `services/data_access/tests/test_schedule_file.py`

**Interfaces:**
- Produces: `ScheduleFile(path: str)` with `load() -> dict` — reads JSON, returns the last good value if the file is missing or mid-edit invalid.

- [ ] **Step 1: Write the failing test**

```python
# services/data_access/tests/test_schedule_file.py
import json

from data_access.schedule import ScheduleFile


def test_load_returns_last_good_on_invalid(tmp_path):
    p = tmp_path / "schedule.json"
    p.write_text(json.dumps({"schedule": [], "live": {}}))
    sf = ScheduleFile(str(p))
    first = sf.load()
    p.write_text("{ not valid json")
    assert sf.load() == first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/data_access && uv run pytest tests/test_schedule_file.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```python
# services/data_access/data_access/schedule.py
import json
import logging

log = logging.getLogger(__name__)


class ScheduleFile:
    """Reads the schedule JSON, returning the last good value if a read fails
    (e.g. a mid-edit save)."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._last: dict | None = None

    def load(self) -> dict:
        try:
            with open(self._path, "rb") as fh:
                self._last = json.load(fh)
        except (OSError, json.JSONDecodeError):
            if self._last is None:
                raise
            log.warning("schedule unreadable; serving last good copy", exc_info=True)
        return self._last
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/data_access && uv run pytest tests/test_schedule_file.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/data_access
git commit -m "feat(data_access): schedule file reader with last-good fallback"
```

---

### Task 10: `configuration` (field.toml → FieldConfig)

**Files:**
- Create: `services/configuration/pyproject.toml`
- Create: `services/configuration/configuration/__init__.py`
- Create: `services/configuration/configuration/appconfig.py`
- Test: `services/configuration/tests/test_appconfig.py`

**Interfaces:**
- Consumes: `GameControllerConfig`, `ObsConfig` (from `data_access.config`); `ScheduleConfig` (from `data_processing.schedule`).
- Produces: `FieldConfig(name, game_controller, obs, schedule)`; `FieldConfig.load_from_file(path: str) -> FieldConfig`.

- [ ] **Step 1: Write the failing test**

```python
# services/configuration/tests/test_appconfig.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/configuration && uv run pytest tests/test_appconfig.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

```toml
# services/configuration/pyproject.toml
[project]
name = "configuration"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["data-access", "data-processing"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.uv.sources]
data-access = { workspace = true }
data-processing = { workspace = true }
```

```python
# services/configuration/configuration/appconfig.py
import tomllib
from dataclasses import dataclass

from data_access.config import GameControllerConfig, ObsConfig
from data_processing.schedule import ScheduleConfig


@dataclass(frozen=True)
class FieldConfig:
    name: str
    game_controller: GameControllerConfig
    obs: ObsConfig
    schedule: ScheduleConfig

    @classmethod
    def load_from_file(cls, path: str) -> "FieldConfig":
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        obs = data["obs"]
        return cls(
            name=data["field"]["name"],
            game_controller=GameControllerConfig(**data["game_controller"]),
            obs=ObsConfig(
                url=obs["url"],
                password=obs["password"],
                sources=dict(obs.get("sources", {})),
                text_field=obs.get("text_field", "text"),
            ),
            schedule=ScheduleConfig(path=data["schedule"]["path"]),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/configuration && uv run pytest tests/test_appconfig.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/configuration
git commit -m "feat(configuration): load field.toml into FieldConfig"
```

---

### Task 11: `obs-live-data` app wiring (remove Flask)

**Files:**
- Create: `services/obs-live-data/pyproject.toml`
- Create: `services/obs-live-data/obs_live_data/__init__.py`
- Create: `services/obs-live-data/obs_live_data/app.py`
- Test: `services/obs-live-data/tests/test_app.py`
- Delete: `services/obs-live-data/app.py`, `services/obs-live-data/schedule_logic.py`, `services/obs-live-data/conftest.py`, `services/obs-live-data/tests/test_app.py` (old Flask), `services/obs-live-data/tests/test_schedule_logic.py`, `services/obs-live-data/requirements.txt`

**Interfaces:**
- Consumes: `RefereeSource`; `ObsText`; `format_updates`; the `sources` map from `ObsConfig`.
- Produces: `async run_referee(source, obs, sources)` — for each `MatchState`, pushes only changed text fields via `obs.set_text`.

- [ ] **Step 1: Write the failing test**

```python
# services/obs-live-data/tests/test_app.py
from data_access.fake import FakeRefereeSource
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from obs_live_data.app import run_referee


class RecordingObs:
    def __init__(self):
        self.calls = []

    async def set_text(self, source_name, value):
        self.calls.append((source_name, value))


def _state(blue_score):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team("ER-Force", blue_score, 0), Team("TIGERs", 0, 0))


async def test_run_pushes_only_changed_fields():
    sources = {"blue_score": "txt_bs", "blue_name": "txt_bn"}
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0)), (0.0, _state(1))])
    await run_referee(src, obs, sources)
    # name unchanged across both states -> pushed once; score changes -> pushed twice
    assert obs.calls == [
        ("txt_bs", "0"), ("txt_bn", "ER-Force"), ("txt_bs", "1"),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/obs-live-data && uv run pytest tests/test_app.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Write minimal implementation**

First remove the old Flask files:

```bash
cd services/obs-live-data
git rm app.py schedule_logic.py conftest.py requirements.txt tests/test_app.py tests/test_schedule_logic.py
mkdir -p obs_live_data
```

```toml
# services/obs-live-data/pyproject.toml
[project]
name = "obs-live-data"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["configuration", "data-access", "data-processing", "data-structures"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.uv.sources]
configuration = { workspace = true }
data-access = { workspace = true }
data-processing = { workspace = true }
data-structures = { workspace = true }
```

```python
# services/obs-live-data/obs_live_data/app.py
from data_processing.format import format_updates


async def run_referee(source, obs, sources: dict[str, str]) -> None:
    """Push live referee-derived text to OBS, sending only fields whose value
    changed since the last push (last-write-wins)."""
    last: dict[str, str] = {}
    async for state in source:
        updates = format_updates(state, None, sources)
        for name, value in updates.items():
            if last.get(name) != value:
                await obs.set_text(name, value)
                last[name] = value
```

```python
# services/obs-live-data/obs_live_data/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/obs-live-data && uv run pytest tests/test_app.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/obs-live-data
git commit -m "feat(obs-live-data): event-driven referee->OBS push (drop Flask)"
```

---

### Task 12: Entry point, `field.toml.example`, docs

**Files:**
- Create: `services/obs-live-data/obs_live_data/__main__.py`
- Create: `services/obs-live-data/field.toml.example`
- Modify: `services/obs-live-data/README.md`
- Modify: `docs/INSTALL.md` (update the run line for obs-live-data)
- Test: `services/obs-live-data/tests/test_main_wiring.py`

**Interfaces:**
- Consumes: `FieldConfig`, `ObsText`, `MulticastRefereeSource`, `ScheduleFile`, `decode_referee`, `run_referee`.
- Produces: `build_source(config) -> MulticastRefereeSource` (wires the injected `decode_referee`); `async main(config_path: str)`.

- [ ] **Step 1: Write the failing test**

```python
# services/obs-live-data/tests/test_main_wiring.py
from data_access.config import GameControllerConfig
from data_processing.decode import decode_referee
from obs_live_data.__main__ import build_source


def test_build_source_injects_real_decoder():
    src = build_source(GameControllerConfig("224.5.23.1", 10003))
    assert src._decode is decode_referee
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/obs-live-data && uv run pytest tests/test_main_wiring.py -v`
Expected: FAIL (no `__main__`).

- [ ] **Step 3: Write minimal implementation**

```python
# services/obs-live-data/obs_live_data/__main__.py
import asyncio
import sys

import simpleobsws
from configuration.appconfig import FieldConfig
from data_access.config import GameControllerConfig
from data_access.gc import MulticastRefereeSource
from data_access.obs import ObsText
from data_processing.decode import decode_referee

from obs_live_data.app import run_referee


def build_source(gc: GameControllerConfig) -> MulticastRefereeSource:
    return MulticastRefereeSource(gc, decode_referee)


async def main(config_path: str) -> None:
    config = FieldConfig.load_from_file(config_path)
    ws = simpleobsws.WebSocketClient(url=config.obs.url, password=config.obs.password)
    await ws.connect()
    await ws.wait_until_identified()
    obs = ObsText(ws, text_field=config.obs.text_field)
    source = build_source(config.game_controller)
    await source.start()
    try:
        await run_referee(source, obs, config.obs.sources)
    finally:
        await ws.disconnect()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "field.toml"))
```

```toml
# services/obs-live-data/field.toml.example
[field]
name = "A"

[game_controller]
address = "224.5.23.1"
port = 10003

[obs]
url = "ws://localhost:4455"
password = "change-me"
text_field = "text"   # FreeType2 text source on Linux uses "text"

[obs.sources]
blue_name = "txt_blue_name"
blue_score = "txt_blue_score"
yellow_name = "txt_yellow_name"
yellow_score = "txt_yellow_score"
stage = "txt_stage"
next_match = "txt_next_match"
countdown = "txt_countdown"

[schedule]
path = "data/schedule.json"
```

Update `services/obs-live-data/README.md` to describe: copy `field.toml.example` → `field.toml`, set OBS url/password + source names, then `uv run python -m obs_live_data field.toml`. Update the `docs/INSTALL.md` run line for obs-live-data accordingly (remove the obs-urlsource mention).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/obs-live-data && uv run pytest tests/test_main_wiring.py -v`
Expected: PASS.

- [ ] **Step 5: Full workspace test + commit**

```bash
cd services && uv run pytest
git add services docs/INSTALL.md
git commit -m "feat(obs-live-data): entry point, field.toml example, docs"
```

---

## Self-Review

- **Spec coverage:** configuration (Task 10) ✓; data_structures domain+proto (1,2) ✓; data_access gc/fake/obs/schedule (6–9) ✓; data_processing decode/format/schedule (3–5) ✓; thin app push loop (11) + entry point (12) ✓; single-field, push-only, event-driven honored throughout; tests use fake source + stub OBS, no network/OBS ✓.
- **Deferred (per spec):** countdown/next-up periodic ticker is wired via `format_updates` (schedule path supported) but the timer task itself is intentionally minimal in this increment — the referee push path is the tested deliverable; a periodic schedule push can be a fast follow once verified against OBS.
- **Type consistency:** `decode_referee(bytes)->MatchState`, `format_updates(state, view, sources)->dict`, `ObsText.set_text(name, value)`, `run_referee(source, obs, sources)`, `FieldConfig.load_from_file(path)` — names match across consumer tasks.
- **Dependency direction:** data_access/data_processing → data_structures only; configuration → data_access + data_processing; obs-live-data → all. Acyclic.
