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
- Concern-based Python libraries that listen to the GC `Referee` feed, decode it into clean
  domain objects, and push text to OBS.
- A `RefereeSource` abstraction with a real (multicast) and a fake (in-process) implementation.
- A shared per-field configuration file.
- `obs-live-data` reworked as a thin app that wires it together for a single field.

Out of scope (deferred): the OBS scene template, scene switching / stream start-stop
(`obs-controller`, MVP2), the AR overlay track, log replay.

## Operating context

- **One `obs-live-data` per field.** A field has its own cameras, OBS, and Game Controller, so
  the app knows a single field's schedule and a single GC feed — no field selection or routing.
- **Push, not pull.** OBS is driven over **obs-websocket v5** (built into OBS 28+) using
  `simpleobsws` directly. The `obs-urlsource` pull plugin is dropped (unreliable on Linux).
- **Event-driven, single asyncio loop, one process.** No threads, no multi-process
  supervision. The multicast socket and the OBS connection live on the same loop.

## Configuration (shared, one per field)

A single root **`field.toml`** describes everything known about a field up front; every
application reads what it needs from it. A `configuration` library loads it once into a
`FieldConfig`. Each concern library owns its own config dataclass; `configuration` aggregates
them (mirrors `tdp_rust`'s central `configuration` crate). TOML is language-agnostic, so
non-Python apps (graphics) can read it later too.

```toml
[field]
name = "A"

[game_controller]          # data_access
address = "224.5.23.1"
port = 10003

[obs]                      # data_access
url = "ws://localhost:4455"
password = "..."

[obs.sources]              # logical field -> OBS text-source name (the source-name map)
blue_name = "..."
blue_score = "..."
yellow_name = "..."
yellow_score = "..."
stage = "..."
next_match = "..."
countdown = "..."

[schedule]                 # data_processing
path = "data/schedule.json"
```

Env-var overrides optional (e.g. `SSL_OBS__PASSWORD=...`) but not required for this increment.

## Architecture

Concern-based libraries (intent borrowed from `tdp_rust`, right-sized — not a 1-to-1 copy)
plus thin app binaries, all in a single `uv` workspace under `services/`:

```
configuration/    central per-field config
data_structures/  pure domain types + the source interface + vendored proto/_pb2
data_access/       external IO: GC multicast, fake source, OBS websocket, schedule file
data_processing/   pure logic: decode, format, schedule resolve
obs-live-data/     thin app: the asyncio event loop that wires the libs for one field
obs-controller/    thin app (MVP2): reuses the same libs
```

`data_structures` / `data_access` / `data_processing` are the durable, reusable boundaries that
`obs-controller` will also import. `obs-live-data` is a thin wiring binary. No separate
OBS-client library — `simpleobsws` is already the client; the small set/reconnect helpers live
in `data_access.obs`. The event-driven fan-out is just the app's loop, so there is no separate
`event_processing` package.

### data_structures (library, pure)

No protobuf or IO leaks outward.

- `domain.py` — `Team{ name: str, score: int, yellow_cards: int }`,
  `MatchState{ stage: Stage, command: Command, blue: Team, yellow: Team }`.
- `enums.py` — `Stage`, `Command`, mirroring the proto. Display strings are a formatting
  concern (in `data_processing`), not here.
- `sources.py` — `RefereeSource`, an async-iterable protocol: `async for state in source`
  yields each new `MatchState`. (Interface here; implementations in `data_access`.)
- `proto/` — vendored GC `Referee` proto set (`ssl_gc_referee_message.proto` plus its imports)
  and the generated `_pb2` modules, with a regen script. Mirrors `ssl_calib`'s vendoring.

### data_access (library, external IO)

- `gc.py` — `MulticastRefereeSource(GameControllerConfig, decode)`: joins the GC multicast
  group and yields `MatchState`. The `decode` function is **injected** (the app passes
  `data_processing.decode_referee`) so `data_access` depends only on `data_structures`, never
  "up" into `data_processing`.
- `fake.py` — `FakeRefereeSource(script)`: yields a scripted sequence of `MatchState`s
  **in-process**, with `await`ed delays for timing. No network — safe on a shared venue
  network. Same `RefereeSource` interface, so it is dependency-injected behind the real one.
- `obs.py` — thin `simpleobsws` usage: connect / wait-until-identified / reconnect, and
  `set_text(source_name, value)` issuing `SetInputSettings`. (The OBS text setting key differs
  by source type; on Linux the FreeType2 source uses `text`. Configurable.)
- `schedule.py` — read (and hot-reload) the schedule file.
- Owns the `GameControllerConfig` and `ObsConfig` dataclasses consumed by `configuration`.

### data_processing (library, pure)

- `decode.py` — `decode_referee(payload: bytes) -> MatchState`. The core unit-tested function.
- `format.py` — pure functions mapping `MatchState` (+ schedule state) to `{source_name: text}`
  updates. The display strings for stages/commands live here.
- `schedule.py` — single-field schedule resolve (now / next / countdown), simplified from the
  current multi-field `schedule_logic.py` (drop the field argument). Owns `ScheduleConfig`.

### obs-live-data (thin app)

- `app.py` — one asyncio loop:
  1. load `FieldConfig`; connect the OBS client (with reconnect),
  2. build the `RefereeSource` (real or fake, per config/DI),
  3. `async for state in source:` → `format` → push changed text fields via `data_access.obs`,
  4. a periodic task ticks the schedule countdown / next-up and pushes those.
- The markdown→json schedule importer (`import_schedule.py`) and schedule data carry over; the
  old Flask/HTTP layer is removed.

## Data flow

```
GC Referee (UDP multicast)            FakeRefereeSource (in-process, tests/dev)
            │                                     │
            └──────────► RefereeSource ◄──────────┘   (data_structures interface;
                              │  async for state        impls in data_access)
                              ▼
                       obs-live-data app
              data_processing.format(MatchState, schedule)
                              │  {source_name: text}
                              ▼
                 data_access.obs.set_text  (simpleobsws SetInputSettings)
                              ▼
                        OBS native text
```

## Error handling

- **OBS connection:** connect/identify on start; on drop, retry with backoff; keep the latest
  desired text per source (last-write-wins) and re-push on reconnect.
- **Malformed datagram:** `decode_referee` raises; `MulticastRefereeSource` logs and skips that
  packet, keeps listening.
- **Schedule file:** invalid/mid-edit save → keep serving last good schedule (existing
  hot-reload behaviour carries over).

## Testing (no real OBS, no network)

- `data_processing.decode`: construct a `Referee` via the generated `_pb2`, serialize, decode,
  assert the `MatchState`. Golden-bytes coverage of stages/commands/scores/names.
- `data_processing.format`: pure `MatchState`→updates assertions, including display strings.
- `data_processing.schedule`: now/next/countdown/edge cases (carried from existing tests).
- `obs-live-data`: run the loop with a `FakeRefereeSource` script and a recording stub OBS
  client; assert the exact `set_text` calls in order.
- `MulticastRefereeSource`: a loopback smoke test, run manually — not in CI (keeps the wire
  clean by default).

## Tooling & conventions

- `uv` workspace; each library and app is a member with its own `pyproject.toml` (mirrors the
  per-crate `Cargo.toml` layout).
- Small, single-purpose files; dataclasses; full type hints; readable names; comments only for
  *why*, not *what*.
- The pure layers (`decode`, `format`, `schedule`) are the unit-tested core; the async wiring
  is verified with the fake source + stub client.

## File layout

```
field.toml                       # shared per-field config (root, or per-deployment)

services/                        # uv workspace
  configuration/
    pyproject.toml
    configuration/
      __init__.py
      appconfig.py               # FieldConfig, load_from_file
  data_structures/
    pyproject.toml
    data_structures/
      __init__.py
      domain.py
      enums.py
      sources.py                 # RefereeSource protocol
      proto/                     # vendored .proto + generated _pb2 + regen script
  data_access/
    pyproject.toml
    data_access/
      __init__.py
      gc.py                      # MulticastRefereeSource
      fake.py                    # FakeRefereeSource
      obs.py                     # simpleobsws set_text + reconnect; ObsConfig
      schedule.py                # schedule file read/watch
      config.py                  # GameControllerConfig, ObsConfig
  data_processing/
    pyproject.toml
    data_processing/
      __init__.py
      decode.py
      format.py
      schedule.py                # resolve now/next/countdown (single field); ScheduleConfig
  obs-live-data/
    pyproject.toml
    obs_live_data/
      __init__.py
      app.py
    data/                        # schedule.md / schedule.json (carried over)
    import_schedule.py           # carried over
    tests/
  obs-controller/                # thin app, MVP2 scaffold (unchanged)
```
