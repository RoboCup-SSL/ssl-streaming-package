# OBS Scoreboard Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push the same match information the ssl-status-board shows to native OBS sources, as a uniform deduped websocket push.

**Architecture:** Extend the GC proto/decode/domain to carry the missing fields, format them into display strings in `data_processing/format.py`, and push every field to its canonical OBS source name (deduped). Drop the logical→OBS name mapping and the `[obs.sources]`/`[obs.images]` config entirely.

**Tech Stack:** Python 3.12, uv workspace, protobuf (`protoc`), simpleobsws, pytest (asyncio auto).

## Global Constraints

- Canonical source name IS the contract; no mapping, no `GetInputList` discovery. Missing OBS sources are a silent no-op.
- `stage_time_left` is `sint64`; `current_action_time_remaining` is `int64` (not sint64). `next_command` is proto3 `optional` (presence via `HasField`).
- Times are microseconds; clock display matches the board's `formatDuration`: `0 -> "0:00"`, else `"MM:SS"` (both padded), `ceil` of seconds, `-` prefix when negative.
- Regenerate proto with `protoc` (installed); `grpc_tools` is NOT installed.
- New domain fields get defaults so existing constructions keep working.
- TDD, frequent commits. Run tests from `services/`: `uv run pytest -q`.

---

### Task 1: Extend proto + domain

**Files:**
- Modify: `services/data_structures/data_structures/proto/ssl_gc_referee.proto`
- Modify: `services/data_structures/data_structures/proto/regen.sh`
- Regenerate: `services/data_structures/data_structures/proto/ssl_gc_referee_pb2.py`
- Modify: `services/data_structures/data_structures/domain.py`

**Interfaces:**
- Produces: `Team(name, score, yellow_cards, red_cards=0, yellow_card_times=(), timeout_time=0, substitution_allowed=False, substitution_intent=False, substitution_time_left=0)`; `MatchState(stage, command, blue, yellow, stage_time_left=0, next_command=None, action_time_remaining=0)`.

- [ ] **Step 1: Add proto fields.** In `Referee`, after `command_timestamp`, add:
```proto
  optional Command next_command = 12;
  int64 current_action_time_remaining = 15;
```
In `TeamInfo`, after `yellow_cards = 5;`, add:
```proto
    uint32 timeout_time = 7;
    bool bot_substitution_intent = 14;
    bool bot_substitution_allowed = 16;
    uint32 bot_substitution_time_left = 18;
```

- [ ] **Step 2: Point regen.sh at protoc.** Replace the generate line with:
```bash
protoc -I. --python_out=. ssl_gc_referee.proto
```

- [ ] **Step 3: Regenerate.** Run from the proto dir: `protoc -I. --python_out=. ssl_gc_referee.proto`. Verify import: `cd services && uv run python -c "from data_structures.proto import ssl_gc_referee_pb2 as pb; r=pb.Referee(); r.next_command=12; assert r.HasField('next_command')"`.

- [ ] **Step 4: Extend domain dataclasses** in `domain.py`:
```python
from dataclasses import dataclass, field

from data_structures.enums import Command, Stage


@dataclass(frozen=True)
class Team:
    name: str
    score: int
    yellow_cards: int
    red_cards: int = 0
    yellow_card_times: tuple[int, ...] = ()
    timeout_time: int = 0
    substitution_allowed: bool = False
    substitution_intent: bool = False
    substitution_time_left: int = 0


@dataclass(frozen=True)
class MatchState:
    stage: Stage
    command: Command
    blue: Team
    yellow: Team
    stage_time_left: int = 0
    next_command: Command | None = None
    action_time_remaining: int = 0
```

- [ ] **Step 5: Run suite** (`cd services && uv run pytest -q`) — must stay green (defaults keep old constructions valid). Commit: `git commit -am "feat(data-structures): extend GC proto + domain for scoreboard fields"`.

---

### Task 2: Decode the new fields

**Files:**
- Modify: `services/data_processing/data_processing/decode.py`
- Modify: `services/data_processing/tests/test_decode.py`

**Interfaces:**
- Consumes: proto + domain from Task 1.
- Produces: `decode_referee(payload: bytes) -> MatchState` populating all new fields.

- [ ] **Step 1: Extend the test.** Append to `test_decode.py`:
```python
def _full_payload():
    ref = pb.Referee(stage=1, command=16, command_counter=1, command_timestamp=1)
    ref.stage_time_left = 123_000_000
    ref.next_command = 9  # DIRECT_FREE_BLUE
    ref.current_action_time_remaining = -5_000_000
    ref.blue.name, ref.blue.score, ref.blue.yellow_cards = "ER-Force", 1, 1
    ref.blue.red_cards = 2
    ref.blue.yellow_card_times.extend([5_000_000, 9_000_000])
    ref.blue.timeout_time = 240_000_000
    ref.blue.bot_substitution_intent = True
    ref.yellow.name, ref.yellow.score, ref.yellow.yellow_cards = "TIGERs", 2, 0
    ref.yellow.bot_substitution_allowed = True
    ref.yellow.bot_substitution_time_left = 18_000_000
    return ref.SerializeToString()


def test_decode_referee_maps_new_fields():
    state = decode_referee(_full_payload())
    assert state.stage_time_left == 123_000_000
    assert state.next_command is Command.DIRECT_FREE_BLUE
    assert state.action_time_remaining == -5_000_000
    assert state.blue.red_cards == 2
    assert state.blue.yellow_card_times == (5_000_000, 9_000_000)
    assert state.blue.timeout_time == 240_000_000
    assert state.blue.substitution_intent is True
    assert state.yellow.substitution_allowed is True
    assert state.yellow.substitution_time_left == 18_000_000


def test_decode_referee_next_command_absent_is_none():
    ref = pb.Referee(stage=1, command=0, command_counter=1, command_timestamp=1)
    ref.blue.name, ref.yellow.name = "B", "Y"
    assert decode_referee(ref.SerializeToString()).next_command is None
```

- [ ] **Step 2: Run, expect FAIL** (`uv run pytest data_processing/tests/test_decode.py -q`) — AttributeError/assertion on new fields.

- [ ] **Step 3: Implement decode:**
```python
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage
from data_structures.proto import ssl_gc_referee_pb2 as pb


def _team(info: pb.Referee.TeamInfo) -> Team:
    return Team(
        name=info.name,
        score=info.score,
        yellow_cards=info.yellow_cards,
        red_cards=info.red_cards,
        yellow_card_times=tuple(info.yellow_card_times),
        timeout_time=info.timeout_time,
        substitution_allowed=info.bot_substitution_allowed,
        substitution_intent=info.bot_substitution_intent,
        substitution_time_left=info.bot_substitution_time_left,
    )


def decode_referee(payload: bytes) -> MatchState:
    ref = pb.Referee()
    ref.ParseFromString(payload)
    return MatchState(
        stage=Stage(ref.stage),
        command=Command(ref.command),
        blue=_team(ref.blue),
        yellow=_team(ref.yellow),
        stage_time_left=ref.stage_time_left,
        next_command=Command(ref.next_command) if ref.HasField("next_command") else None,
        action_time_remaining=ref.current_action_time_remaining,
    )
```

- [ ] **Step 4: Run, expect PASS** (whole suite green). Commit: `git commit -am "feat(data-processing): decode new GC scoreboard fields"`.

---

### Task 3: Format functions

**Files:**
- Modify: `services/data_processing/data_processing/format.py`
- Modify: `services/data_processing/tests/test_format.py`

**Interfaces:**
- Consumes: domain from Task 1.
- Produces: `format_clock(microseconds: int) -> str`, `stage_label(stage) -> str`, `command_text(state) -> str`, `next_command_text(command | None) -> str`, `substitution_text(team) -> str`, `card_time_texts(team) -> list[str]`, `format_updates(state) -> dict[str, str]` (canonical keys).

- [ ] **Step 1: Rewrite `test_format.py`:**
```python
from data_processing.format import (
    card_time_texts,
    command_text,
    format_clock,
    format_updates,
    next_command_text,
    stage_label,
    substitution_text,
)
from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage


def _state(**kw):
    base = dict(
        stage=Stage.NORMAL_FIRST_HALF, command=Command.NORMAL_START,
        blue=Team("ER-Force", 1, 0), yellow=Team("TIGERs", 2, 0),
    )
    base.update(kw)
    return MatchState(**base)


def test_format_clock_zero_and_padding():
    assert format_clock(0) == "0:00"
    assert format_clock(8_000_000) == "00:08"
    assert format_clock(125_000_000) == "02:05"


def test_format_clock_ceils_and_signs():
    assert format_clock(1_200_000) == "00:02"      # ceil of 1.2s
    assert format_clock(-5_000_000) == "-00:05"


def test_stage_label_uses_board_wording():
    assert stage_label(Stage.NORMAL_FIRST_HALF) == "1st Half"
    assert stage_label(Stage.NORMAL_HALF_TIME) == "Half Time"
    assert stage_label(Stage.POST_GAME) == "Match finished"


def test_command_text_embeds_team_and_inline_times():
    assert command_text(_state(command=Command.DIRECT_FREE_BLUE)) == "Free Kick for Blue"
    assert command_text(_state(command=Command.HALT)) == "Halt"
    bp = _state(command=Command.BALL_PLACEMENT_BLUE, action_time_remaining=8_000_000)
    assert command_text(bp) == "Ball Placement for Blue (00:08)"
    to = _state(command=Command.TIMEOUT_YELLOW,
                yellow=Team("TIGERs", 2, 0, timeout_time=83_000_000))
    assert command_text(to) == "Timeout for Yellow (01:23)"


def test_next_command_text():
    assert next_command_text(None) == ""
    assert next_command_text(Command.PREPARE_KICKOFF_YELLOW) == "Next: Kickoff for Yellow"


def test_substitution_text():
    assert substitution_text(Team("B", 0, 0)) == ""
    assert substitution_text(Team("B", 0, 0, substitution_intent=True)) == "Substitution Requested"
    active = Team("B", 0, 0, substitution_allowed=True, substitution_time_left=18_000_000)
    assert substitution_text(active) == "Substitution Active (00:18)"


def test_card_time_texts_caps_at_two():
    team = Team("B", 0, 0, yellow_card_times=(5_000_000, 9_000_000, 12_000_000))
    assert card_time_texts(team) == ["00:05", "00:09"]
    assert card_time_texts(Team("B", 0, 0)) == []


def test_format_updates_emits_all_canonical_keys():
    out = format_updates(_state(
        stage_time_left=125_000_000,
        blue=Team("ER-Force", 1, 1, red_cards=2, yellow_card_times=(5_000_000,)),
    ))
    assert out["blue_name"] == "ER-Force"
    assert out["blue_score"] == "1"
    assert out["yellow_score"] == "2"
    assert out["stage"] == "1st Half"
    assert out["stage_time"] == "02:05"
    assert out["command"] == "Normal Start"
    assert out["next_command"] == ""
    assert out["blue_yellow_cards"] == "1"
    assert out["blue_red_cards"] == "2"
    assert out["blue_card_time_1"] == "00:05"
    assert out["blue_card_time_2"] == ""      # blank-filled to two
    assert out["yellow_card_time_1"] == ""
    assert out["blue_substitution"] == ""
```

- [ ] **Step 2: Run, expect FAIL** (`uv run pytest data_processing/tests/test_format.py -q`).

- [ ] **Step 3: Rewrite `format.py`:**
```python
import math

from data_structures.domain import MatchState, Team
from data_structures.enums import Command, Stage

_STAGE_LABELS = {
    Stage.NORMAL_FIRST_HALF_PRE: "Match to be started",
    Stage.NORMAL_FIRST_HALF: "1st Half",
    Stage.NORMAL_HALF_TIME: "Half Time",
    Stage.NORMAL_SECOND_HALF_PRE: "2nd Half",
    Stage.NORMAL_SECOND_HALF: "2nd Half",
    Stage.EXTRA_TIME_BREAK: "Game goes into Overtime",
    Stage.EXTRA_FIRST_HALF_PRE: "1st Half (Overtime)",
    Stage.EXTRA_FIRST_HALF: "1st Half (Overtime)",
    Stage.EXTRA_HALF_TIME: "Half Time (Overtime)",
    Stage.EXTRA_SECOND_HALF_PRE: "2nd Half (Overtime)",
    Stage.EXTRA_SECOND_HALF: "2nd Half (Overtime)",
    Stage.PENALTY_SHOOTOUT_BREAK: "Prepare for Penalty Shootout",
    Stage.PENALTY_SHOOTOUT: "Penalty Shootout",
    Stage.POST_GAME: "Match finished",
}

_COMMAND_TEXT = {
    Command.HALT: "Halt",
    Command.STOP: "Stop",
    Command.NORMAL_START: "Normal Start",
    Command.FORCE_START: "Force Start",
    Command.PREPARE_KICKOFF_YELLOW: "Kickoff for Yellow",
    Command.PREPARE_KICKOFF_BLUE: "Kickoff for Blue",
    Command.PREPARE_PENALTY_YELLOW: "Penalty Kick for Yellow",
    Command.PREPARE_PENALTY_BLUE: "Penalty Kick for Blue",
    Command.DIRECT_FREE_YELLOW: "Free Kick for Yellow",
    Command.DIRECT_FREE_BLUE: "Free Kick for Blue",
    Command.INDIRECT_FREE_YELLOW: "Free Kick for Yellow",
    Command.INDIRECT_FREE_BLUE: "Free Kick for Blue",
    Command.TIMEOUT_YELLOW: "Timeout for Yellow",
    Command.TIMEOUT_BLUE: "Timeout for Blue",
    Command.GOAL_YELLOW: "Goal for Yellow",
    Command.GOAL_BLUE: "Goal for Blue",
    Command.BALL_PLACEMENT_YELLOW: "Ball Placement for Yellow",
    Command.BALL_PLACEMENT_BLUE: "Ball Placement for Blue",
}


def stage_label(stage: Stage) -> str:
    return _STAGE_LABELS[stage]


def format_clock(microseconds: int) -> str:
    """Match the status board's formatDuration: 0 -> '0:00', else 'MM:SS' (padded),
    ceiling of seconds, '-' prefix when negative (overtime)."""
    if microseconds == 0:
        return "0:00"
    sign = "-" if microseconds < 0 else ""
    total = math.ceil(abs(microseconds) / 1_000_000)
    minutes, seconds = divmod(total, 60)
    return f"{sign}{minutes:02d}:{seconds:02d}"


def command_text(state: MatchState) -> str:
    text = _COMMAND_TEXT[state.command]
    if state.command in (Command.BALL_PLACEMENT_BLUE, Command.BALL_PLACEMENT_YELLOW):
        if state.action_time_remaining >= 0:
            text += f" ({format_clock(state.action_time_remaining)})"
    elif state.command is Command.TIMEOUT_BLUE:
        text += f" ({format_clock(state.blue.timeout_time)})"
    elif state.command is Command.TIMEOUT_YELLOW:
        text += f" ({format_clock(state.yellow.timeout_time)})"
    return text


def next_command_text(command: Command | None) -> str:
    if command is None:
        return ""
    return f"Next: {_COMMAND_TEXT[command]}"


def substitution_text(team: Team) -> str:
    if team.substitution_allowed:
        text = "Substitution Active"
    elif team.substitution_intent:
        text = "Substitution Requested"
    else:
        return ""
    if team.substitution_time_left > 0:
        text += f" ({format_clock(team.substitution_time_left)})"
    return text


def card_time_texts(team: Team) -> list[str]:
    return [format_clock(t) for t in team.yellow_card_times[:2]]


def format_updates(state: MatchState) -> dict[str, str]:
    """Canonical-key -> display string for every scoreboard field. Pushed deduped;
    the key is the OBS source name."""
    updates = {
        "blue_name": state.blue.name,
        "yellow_name": state.yellow.name,
        "blue_score": str(state.blue.score),
        "yellow_score": str(state.yellow.score),
        "stage": stage_label(state.stage),
        "stage_time": format_clock(state.stage_time_left),
        "command": command_text(state),
        "next_command": next_command_text(state.next_command),
        "blue_yellow_cards": str(state.blue.yellow_cards),
        "yellow_yellow_cards": str(state.yellow.yellow_cards),
        "blue_red_cards": str(state.blue.red_cards),
        "yellow_red_cards": str(state.yellow.red_cards),
        "blue_substitution": substitution_text(state.blue),
        "yellow_substitution": substitution_text(state.yellow),
    }
    for side, team in (("blue", state.blue), ("yellow", state.yellow)):
        times = card_time_texts(team)
        for i in range(2):
            updates[f"{side}_card_time_{i + 1}"] = times[i] if i < len(times) else ""
    return updates
```

- [ ] **Step 4: Run, expect PASS** (`uv run pytest data_processing/tests/test_format.py -q`). Commit: `git commit -am "feat(data-processing): format scoreboard fields to board-parity strings"`.

---

### Task 4: Push layer + config removal

**Files:**
- Modify: `services/obs-live-data/obs_live_data/app.py`
- Modify: `services/obs-live-data/tests/test_app.py`
- Modify: `services/data_access/data_access/config.py`
- Modify: `services/configuration/configuration/appconfig.py`
- Modify: `services/configuration/tests/test_appconfig.py`
- Modify: `services/obs-live-data/obs_live_data/__main__.py`
- Modify: `services/obs-live-data/obs_live_data/demo.py`
- Modify: `field.toml.example`

**Interfaces:**
- Consumes: `format_updates(state)` from Task 3.
- Produces: `run_referee(source, obs, logos_dir="logos")`; `resolve_images(state, logos_dir) -> dict[str,str]`; `ObsConfig(url, password, logos_dir="", stage_dir="", text_field="text")`.

- [ ] **Step 1: Update `app.py`** — change `resolve_images` and `run_referee` signatures:
```python
def resolve_images(state, logos_dir: str) -> dict[str, str]:
    """OBS image-source name -> absolute logo path for both team logos."""
    teams = {"blue_logo": state.blue.name, "yellow_logo": state.yellow.name}
    return {key: _logo_path(name, logos_dir) for key, name in teams.items()}


async def run_referee(source, obs, logos_dir: str = "logos") -> None:
    """Push live referee-derived text and team logos to OBS, sending only values
    that changed since the last push (last-write-wins per source name)."""
    last: dict[str, str] = {}
    async for state in source:
        for name, value in format_updates(state).items():
            if last.get(name) != value:
                await obs.set_text(name, value)
                last[name] = value
        for name, path in resolve_images(state, logos_dir).items():
            if last.get(name) != path:
                await obs.set_image(name, path)
                last[name] = path
```
Remove the now-unused `format_updates` extra args and the `image_sources`/`text_sources` references. Keep `_logo_path`, `bundled_logos_dir`, `effective_logos_dir`, and the `format_updates`/`resolve_images` imports.

- [ ] **Step 2: Rewrite the push tests** in `test_app.py` (replace `test_run_pushes_only_changed_fields` and `test_run_pushes_team_logos`; keep the `effective_logos_dir` tests and `RecordingObs`):
```python
def _state(blue_score, blue_name="ER-Force", yellow_name="TIGERs"):
    return MatchState(Stage.NORMAL_FIRST_HALF, Command.NORMAL_START,
                      Team(blue_name, blue_score, 0), Team(yellow_name, 0, 0))


async def test_run_pushes_changed_fields_only():
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0)), (0.0, _state(1))])
    await run_referee(src, obs, "logos")
    # blue_score appears once per state (changed), blue_name only once (unchanged).
    assert ("blue_name", "ER-Force") in obs.calls
    assert obs.calls.count(("blue_score", "0")) == 1
    assert obs.calls.count(("blue_score", "1")) == 1
    assert obs.calls.count(("blue_name", "ER-Force")) == 1


async def test_run_pushes_team_logos(tmp_path):
    (tmp_path / "er-force.png").write_bytes(b"x")
    (tmp_path / "no-logo.png").write_bytes(b"x")
    obs = RecordingObs()
    src = FakeRefereeSource([(0.0, _state(0, yellow_name="Nonexistent"))])
    await run_referee(src, obs, str(tmp_path))
    assert obs.images == [
        ("blue_logo", os.path.abspath(str(tmp_path / "er-force.png"))),
        ("yellow_logo", os.path.abspath(str(tmp_path / "no-logo.png"))),
    ]
```

- [ ] **Step 3: Run, expect FAIL** (`uv run pytest obs-live-data/tests/test_app.py -q`).

- [ ] **Step 4: Slim `ObsConfig`** in `config.py`:
```python
@dataclass(frozen=True)
class ObsConfig:
    url: str
    password: str
    logos_dir: str = ""
    stage_dir: str = ""
    text_field: str = "text"
```
Remove the `field` import if now unused (GameControllerConfig doesn't use it).

- [ ] **Step 5: Update `appconfig.py`** — drop sources/images from the `ObsConfig(...)` construction:
```python
            obs=ObsConfig(
                url=obs["url"],
                password=obs["password"],
                logos_dir=obs.get("logos_dir", ""),
                stage_dir=obs.get("stage_dir", ""),
                text_field=obs.get("text_field", "text"),
            ),
```

- [ ] **Step 6: Update `test_appconfig.py`** — remove the `[obs.sources]`/`[obs.images]` blocks from the TOML and the two assertions on `cfg.obs.sources`/`cfg.obs.images`. Keep the rest (name, port, logos_dir, schedule.path).

- [ ] **Step 7: Update `__main__.py`** — call `run_referee(source, obs, logos_dir)` (drop `config.obs.sources, config.obs.images`). No other change.

- [ ] **Step 8: Update `demo.py`** — call `run_referee(FakeRefereeSource(SCRIPT), obs, logos_dir)`; reduce `_preflight` to list OBS inputs only (no configured-name comparison):
```python
async def _preflight(client) -> None:
    """List OBS's actual inputs so you can confirm your sources are named to match
    the canonical field names (see obs-template/README.md)."""
    response = await client.call(simpleobsws.Request("GetInputList"))
    inputs = sorted(i["inputName"] for i in response.responseData.get("inputs", []))
    print(f"OBS inputs ({len(inputs)}): {inputs}")
```
Update its call site to `await _preflight(client)`.

- [ ] **Step 9: Clean `field.toml.example`** — delete the `[obs.sources]` and `[obs.images]` blocks and the leading comment paragraph about source names. Replace that comment with:
```toml
# Name your OBS Text and Image sources to match the canonical field names listed in
# obs-template/README.md (e.g. "blue_name", "stage_time", "blue_logo"). Sources you
# don't create are simply not shown.
```

- [ ] **Step 10: Run full suite, expect PASS** (`cd services && uv run pytest -q`). Commit: `git commit -am "feat(obs-live-data): push all scoreboard fields by canonical name; drop source mapping"`.

---

### Task 5: Field-name reference docs

**Files:**
- Modify: `obs-template/README.md`

**Interfaces:** none (docs).

- [ ] **Step 1: Document the canonical source names** in `obs-template/README.md` — list every Text source name and every Image source name from the spec's field table, grouped (per-team, center), each with a one-line description, plus a note that unmatched names are silently skipped and that the build-your-scene step is to create sources with these exact names.

- [ ] **Step 2: Commit** `git commit -am "docs(obs-template): canonical OBS source-name reference"`.

---

## Self-Review

- **Spec coverage:** proto/domain (T1), decode (T2), format incl. all formatters + `format_updates` (T3), push + config removal + `__main__`/`demo`/`field.toml.example` (T4), docs (T5). All spec sections covered.
- **Placeholder scan:** none — every code step shows full code.
- **Type consistency:** `format_updates(state)`, `run_referee(source, obs, logos_dir)`, `resolve_images(state, logos_dir)`, `ObsConfig(url, password, logos_dir, stage_dir, text_field)` consistent across tasks.
- **Out of scope confirmed:** no event log, no status message, no Lua, no generated scene.
