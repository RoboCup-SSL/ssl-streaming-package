# Live match text via OBS websocket — design

Date: 2026-06-18
Status: approved (brainstorm), pre-implementation

## Goal

Push live match information onto the stream — team names, score, match stage — driven by the
SSL Game Controller, with **zero manual typing** by the operator. This is README feature 2.2,
and it establishes the protobuf-listening foundation the rest of the autonomy track (MVP2)
builds on.

## Scope (this increment)

Increment "C": build the real protobuf foundation and prove data flows all the way to OBS
text, **without** depending on the (not-yet-built) OBS template or a real Game Controller.

In scope:
- A reusable library that listens to the GC `Referee` feed and decodes it into clean domain
  objects.
- A `RefereeSource` abstraction with a real (multicast) and a fake (in-process) implementation.
- `obs-live-data` reworked to push text to OBS over websocket on every update, for a single
  field.

Out of scope (deferred): the OBS scene template, scene switching / stream start-stop
(`obs-controller`, MVP2), the AR overlay track, log replay.

## Operating context

- **One `obs-live-data` per field.** A field has its own cameras, its own OBS, and its own
  Game Controller. The app therefore knows a single field's schedule and a single GC feed —
  no field selection, no routing.
- **Push, not pull.** OBS is driven over **obs-websocket v5** (built into OBS 28+) using
  `simpleobsws` directly. The `obs-urlsource` pull plugin is dropped (unreliable on Linux).
- **Event-driven, single asyncio loop, one process.** No threads, no multi-process
  supervision. The multicast socket and the OBS connection live on the same loop.

## Architecture

Two units, both `uv`-managed Python projects:

```
services/
  ssl-protobuf-listener/   library · GC Referee feed → domain objects; RefereeSource
  obs-live-data/           app     · single field; wires a RefereeSource → OBS text
```

`ssl-protobuf-listener` is the durable, reusable boundary; `obs-controller` (MVP2) will import
it too. `obs-live-data` is a thin wiring app. No separate OBS-client library — `simpleobsws`
is already the client; a wrapper would be ceremony. If `obs-controller` later needs shared OBS
helpers, extract them then.

## ssl-protobuf-listener (library)

Python package `ssl_protobuf_listener`.

- **`proto/`** — the vendored GC `Referee` proto set (`ssl_gc_referee_message.proto` plus its
  imports: common, game_event, geometry) and the generated `_pb2` modules, with a regen script.
  Mirrors the vendoring pattern already used in `ssl_calib`.
- **`domain.py`** — plain dataclasses, no protobuf leaking outward:
  - `Team{ name: str, score: int, yellow_cards: int }`
  - `MatchState{ stage: Stage, command: Command, blue: Team, yellow: Team }`
  - `Stage`, `Command` are enums mirroring the proto. Human-readable display strings are a
    formatting concern (in `obs-live-data`), not part of the domain.
- **`decode.py`** — `decode_referee(payload: bytes) -> MatchState`. Pure; the unit-tested layer.
- **`sources.py`** — the event-driven boundary:
  - `RefereeSource` — an async-iterable protocol: `async for state in source` yields each new
    `MatchState`.
  - `MulticastRefereeSource(address, port)` — joins the GC multicast group (default
    `224.5.23.1:10003`, configurable), decodes each datagram, yields the `MatchState`.
  - `FakeRefereeSource(script)` — yields a scripted sequence of `MatchState`s in-process, with
    `await`ed delays for timing. **No network.** Used by tests and local dev.

### Why a fake *source* and not a fake publisher

Injecting real packets onto a multicast group is unsafe at a venue: other teams share the
network and would receive our test traffic. Dependency-injecting a `FakeRefereeSource` keeps
all test/dev message generation inside Python, emits nothing on the wire, and swaps in behind
the same interface the real source implements.

## obs-live-data (app)

Python package `obs_live_data`. Reworked from the current Flask app; the markdown→json
schedule importer and the schedule data carry over, the Flask/HTTP layer is removed.

- **`config.py`** — OBS url + password, the source-name map, the schedule path, and which
  `RefereeSource` to use (real vs fake). The source-name map is a small dict from logical field
  (`blue_name`, `blue_score`, `yellow_name`, `yellow_score`, `stage`, `next_match`, `countdown`)
  to the OBS text-source name the template defines.
- **`schedule.py`** — single-field schedule logic, simplified from the current multi-field
  `schedule_logic.py` (drop the field argument). Pure; supplies "next up" + countdown.
- **`format.py`** — pure functions mapping `MatchState` (and schedule state) to a dict of
  `{source_name: text}` updates. The display strings for stages/commands live here.
- **`obs.py`** — thin `simpleobsws` usage: connect / wait-until-identified / reconnect, and
  `set_text(source_name, value)` issuing `SetInputSettings`. (The OBS text setting key differs
  by source type; on Linux the FreeType2 source uses `text`. Configurable.)
- **`app.py`** — the wiring. One asyncio loop:
  1. connect the OBS client (with reconnect),
  2. `async for state in source:` → `format` → push changed text fields,
  3. a periodic task ticks the schedule countdown / next-up and pushes those.

The `RefereeSource` is injected into `app.run(...)`, so tests pass a `FakeRefereeSource` and a
recording stub OBS client.

## Data flow

```
GC Referee (UDP multicast)            FakeRefereeSource (in-process, tests/dev)
            │                                     │
            └──────────► RefereeSource ◄──────────┘
                              │  async for state
                              ▼
                       obs_live_data.app
                  format(MatchState, schedule)
                              │  {source_name: text}
                              ▼
                    simpleobsws SetInputSettings
                              ▼
                        OBS native text
```

## Error handling

- **OBS connection:** connect/identify on start; on drop, retry with backoff; buffer only the
  latest desired text per source (last-write-wins) and re-push on reconnect.
- **Malformed datagram:** `decode_referee` raises; the multicast source logs and skips that
  packet, keeps listening.
- **Schedule file:** invalid/mid-edit save → keep serving last good schedule (existing
  hot-reload behaviour carries over).

## Testing (no real OBS, no network)

- `decode.py`: construct a `Referee` via the generated `_pb2`, serialize, `decode_referee`,
  assert the `MatchState`. Golden-bytes coverage of stages/commands/scores/names.
- `format.py`: pure `MatchState`→updates assertions, including display strings.
- `app.py`: run the loop with a `FakeRefereeSource` script and a recording stub OBS client;
  assert the exact `set_text` calls in order.
- `MulticastRefereeSource`: a loopback smoke test, run manually — not in CI (keeps the wire
  clean by default).

## Tooling & conventions

- `uv` for both projects (`pyproject.toml`), matching `ssl_calib`.
- Small, single-purpose files; dataclasses; full type hints; readable names; comments only for
  *why*, not *what*.
- The pure layers (`decode`, `schedule`, `format`) are the unit-tested core; the async wiring
  is verified with the fake source + stub client.

## File layout

```
services/ssl-protobuf-listener/
  pyproject.toml
  ssl_protobuf_listener/
    __init__.py
    proto/            # vendored .proto + generated _pb2 + regen script
    domain.py
    decode.py
    sources.py
  tests/

services/obs-live-data/
  pyproject.toml
  obs_live_data/
    __init__.py
    config.py
    schedule.py       # simplified from schedule_logic.py (single field)
    format.py
    obs.py
    app.py
  data/               # schedule.md / schedule.json (carried over)
  import_schedule.py  # carried over
  tests/
```
