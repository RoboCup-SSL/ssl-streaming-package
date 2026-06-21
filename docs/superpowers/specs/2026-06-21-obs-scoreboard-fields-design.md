# OBS scoreboard fields — status-board parity

Date: 2026-06-21
Status: approved (brainstormed with Emiel)

## Goal

Make `obs-live-data` push the same match information the `ssl-status-board` shows, as
native OBS sources, so an operator can build a scoreboard overlay with full parity and
improve the styling from there.

## Scope

In: names, logos, score, stage, current command (with team + inline ball-placement/timeout
countdown), next command, yellow/red card counts, up to two yellow-card timers per team,
substitution state, and the stage clock.

Out (explicitly): the scrolling game-events log, the free-text status message, any starter
OBS scene collection (Emiel builds the scene), and any Lua (the only true ticker — the
schedule countdown — is a separate, parked feature handled by `countdown_to_time.lua`).

## Rendering approach (decided)

Native OBS sources, **uniform deduped push**. Every field is pushed from Python via
`SetInputSettings` on each Game Controller update, deduped to the displayed string (so a
1-second-granularity clock is ~1 push/sec). No browser source. No Lua for the match.

The status board does not tick locally either — it renders whatever the last referee
message carried, at a 10 Hz feed. Mirroring the GC's own values means pause/resume and
overtime (negative clock) come for free.

### No source-name mapping, no discovery

The canonical field name **is** the contract: name an OBS source `blue_name`, `stage_time`,
etc., and we push straight to it. We do not maintain a logical→OBS name mapping and we do
not query `GetInputList` to filter. We push every field; pushing to a source that doesn't
exist is a verified silent no-op (`simpleobsws` returns `requestStatus.result = False`,
code 600 `ResourceNotFound`; we discard the response). The small wasted bandwidth is
accepted in exchange for less code.

The list of field names lives in `obs-template/README.md` (the scene-building doc), not in
`field.toml`.

## Field set → canonical source names

Text sources (create an OBS Text source named exactly):

| Name | Shows |
|---|---|
| `blue_name` / `yellow_name` | team name |
| `blue_score` / `yellow_score` | score |
| `stage` | stage label (board wording, e.g. `1st Half`, `Half Time`) |
| `stage_time` | stage clock `MM:SS` (negative in overtime) |
| `command` | current command incl. team + inline time, e.g. `Free Kick for Blue`, `Ball Placement for Blue (0:08)`, `Timeout for Yellow (1:23)`, `Halt` |
| `next_command` | `Next: Kickoff for Yellow` (blank when none) |
| `blue_yellow_cards` / `yellow_yellow_cards` | yellow-card count |
| `blue_red_cards` / `yellow_red_cards` | red-card count |
| `blue_card_time_1`,`blue_card_time_2` / `yellow_card_time_1`,`yellow_card_time_2` | active yellow-card timers, blank when fewer than two |
| `blue_substitution` / `yellow_substitution` | `Substitution Active (0:18)` / `Substitution Requested` / blank |

Image sources (create an OBS Image source named exactly): `blue_logo`, `yellow_logo`.

## Data pipeline

### Proto (`data_structures/proto/ssl_gc_referee.proto`)

Add (field numbers from the authoritative GC proto, `proto2` original; we declare proto3
which parses the same wire bytes):

- `Referee.optional Command next_command = 12;` — **`optional`** so we distinguish "absent"
  from `HALT (0)` via `HasField`.
- `Referee.int64 current_action_time_remaining = 15;` — **`int64`, not `sint64`** (the GC
  uses non-zigzag here; it differs on the wire for negatives). Only read during ball
  placement, where it is present.
- `TeamInfo.uint32 timeout_time = 7;`
- `TeamInfo.bool bot_substitution_intent = 14;`
- `TeamInfo.bool bot_substitution_allowed = 16;`
- `TeamInfo.uint32 bot_substitution_time_left = 18;`

Already present, currently unused: `stage_time_left = 3` (sint64), `red_cards = 3`,
`yellow_card_times = 4` (repeated uint32), `yellow_cards = 5`.

Regenerate with `protoc` (installed; `grpc_tools` is not). Update `regen.sh` to call
`protoc --python_out=. ssl_gc_referee.proto`.

### Domain (`data_structures/domain.py`), frozen dataclasses

- `Team` gains: `red_cards: int`, `yellow_card_times: tuple[int, ...]`, `timeout_time: int`,
  `substitution_allowed: bool`, `substitution_intent: bool`, `substitution_time_left: int`.
- `MatchState` gains: `stage_time_left: int`, `next_command: Command | None`,
  `action_time_remaining: int`.

All new fields get defaults so existing constructions (tests, demo, fake) keep working.

### Decode (`data_processing/decode.py`)

Map the new proto fields into the domain. `next_command` →
`Command(ref.next_command) if ref.HasField("next_command") else None`. `yellow_card_times`
→ `tuple(info.yellow_card_times)`.

### Format (`data_processing/format.py`) — the testable core

Pure functions, mirroring the board's text/timestamp helpers:

- `format_clock(microseconds: int) -> str` — matches the board's `formatDuration`:
  `0 -> "0:00"`, else `"MM:SS"` (minutes zero-padded), `ceil` of seconds, `-` prefix when
  negative.
- `stage_label(stage) -> str` — adopt the board's `mapStageToText` wording (replaces the
  current labels).
- `command_text(state) -> str` — `_COMMAND_TEXT[command]` (plain, team embedded:
  `Free Kick for Blue`), appending ` (clock)` for ball placement
  (`action_time_remaining`, when `>= 0`) and timeout (the acting team's `timeout_time`).
- `next_command_text(command | None) -> str` — `""` when None, else
  `f"Next: {_COMMAND_TEXT[command]}"`.
- `substitution_text(team) -> str` — `"Substitution Active"` when allowed, else
  `"Substitution Requested"` when intent, else `""`; append ` (clock)` when
  `substitution_time_left > 0`.
- `card_time_texts(team) -> list[str]` — up to two formatted entries from
  `yellow_card_times`.
- `format_updates(state) -> dict[str, str]` — returns the full canonical-keyed dict above.
  Signature changes: drops the old `(schedule_view, sources)` params (the schedule view was
  never wired into the live push; the mapping is gone). Card-timer keys are always present,
  blank-filled to two per team so a cleared card blanks its source.

### Push (`obs-live-data/obs_live_data/app.py`)

`run_referee(source, obs, logos_dir="logos")` — drops the `text_sources`/`image_sources`
params. Loop unchanged: for each state, push every `format_updates` item whose string
changed (dedup via `last`), then every `resolve_images` item whose path changed.
`resolve_images(state, logos_dir)` returns canonical `{"blue_logo": ..., "yellow_logo": ...}`.

### Config (`data_access/config.py`, `configuration/appconfig.py`, `field.toml.example`)

Remove `ObsConfig.sources` and `ObsConfig.images` and their loading. `[obs]` keeps `url`,
`password`, `text_field`, `logos_dir`, `stage_dir`. Delete the `[obs.sources]` and
`[obs.images]` blocks from `field.toml.example`. `__main__.py` and `demo.py` call
`run_referee(source, obs, logos_dir)` and stop referencing `config.obs.sources/images`.
`demo.py`'s preflight (which listed configured vs. existing names) is removed or reduced —
there is no configured list anymore.

## Out-of-scope behavior preserved

- Dedup, reconnect resilience (`ReconnectingObsClient`), clean Ctrl-C — unchanged.
- Logos staging (`stage_dir`) and bundled-logos default — unchanged.

## Testing

- `format.py`: `format_clock` (zero, sub-second ceil, negative/overtime, minutes padding);
  `command_text` per category incl. inline ball-placement and timeout times and plain
  Halt/Stop; `next_command_text` incl. None; `substitution_text` active/requested/blank +
  timer; `card_time_texts` for 0/1/2+ cards; `format_updates` emits every canonical key.
- `decode.py`: build a `pb.Referee`, set new fields (incl. `next_command` present/absent,
  negative `current_action_time_remaining`, yellow-card times), serialize → decode → assert
  the extended `MatchState`/`Team`. Locks wire-compat.
- `app.py`: extend the `run_referee` call-order/dedup test for the new fields — a field
  pushed once, re-pushed only when its string changes.
- Config: update/za­dd `appconfig` test for the slimmed `ObsConfig`.

No new test infrastructure; existing fakes/stubs.

## Migration / breaking changes

Internal only (pre-release). `format_updates`, `run_referee`, and `ObsConfig` signatures
change; `field.toml` `[obs.sources]`/`[obs.images]` are removed. Existing tests for these
are updated in the same change. Stage label strings change to the board's wording.
