# Live match data → OBS native text (via Flask + obs-urlsource) — design

**Date:** 2026-06-16
**Status:** approved (verbal), implementing
**New subsystem:** `live/` (Python — separate from the Remotion graphics)

## REVISION (2026-06-16b) — delivery switched to obs-websocket, localhost-per-machine

After the first build, the deployment model changed. Building/installing the `obs-urlsource`
plugin on every Linux machine was too painful, and a central push-server would have to know
every OBS machine's address. New model — **each machine is fully self-contained**:

- **Topology:** every machine runs its own local `live` process that pushes text into its
  **own local OBS** via OBS's **built-in obs-websocket** (`ws://localhost:4455`, OBS 28+ — no
  plugin to install anywhere). No machine knows about any other; no LAN IPs.
- **Delivery:** the `live` process connects with the `obsws-python` client and calls
  `set_input_settings` on **named native Text (GDI+/FreeType) sources** every ~1 s (so the
  countdown ticks), pushing only changed values, reconnecting if OBS restarts. The Flask HTTP
  server and the `obs-urlsource` wiring described later are **SUPERSEDED**.
- **Named Text sources** the operator creates in OBS (pusher fills any that exist, skips the
  rest): `match_<field>_now`, `match_<field>_next`, `match_<field>_countdown` for field ∈
  {A, B0, B1}. Font/styling live in those native sources, so the scene collection has **no
  plugin dependency** and exports/imports cleanly.
- **Per-PC setup:** install stock OBS → enable Tools ▸ WebSocket Server Settings (+ password)
  → import scene collection → copy `live/` + `schedule.json` → run `OBS_WS_PASSWORD=… python
  live/obs_push.py`. No plugin builds.
- **Per-machine `schedule.json` sync is deferred** (operator copies it manually / USB for now).
- **UNCHANGED:** the pure `schedule_logic.resolve()` / `format_countdown` core and its tests,
  and `import_schedule.py`. Only the *delivery* layer changes (Flask `app.py` → `obs_push.py`).

Everything below this banner that describes the Flask endpoints or `obs-urlsource` is retained
for history but is superseded by this revision.

## Purpose

Auto-fill the on-screen match labels (now-playing, next match, and a countdown) for the
RoboCup 2026 SSL broadcast across **three fields (A, B0, B1)**, so the operator never types
match info into OBS by hand. A small Flask server holds the schedule + a manually-maintained
"what's current" pointer per field, computes now / next / countdown, and exposes it as REST
JSON. OBS pulls that JSON with the **`obs-urlsource`** plugin and renders it in **native text
sources** (operator's own fonts/styling) — no browser source, no HTML/CSS.

The styled layer stays the **pre-rendered graphics we already built** (`NextMatch` card,
`BreathingBackground`, `Standby`); this subsystem only provides the *text* that drops into
their slots. It supersedes the old "operator types the countdown number in OBS" step.

## Why this shape (decided during brainstorming)

- **Manual, file-driven (not clock-driven):** robotics matches always run late/early, so a
  clock-based auto-selector would be wrong all day. The operator edits one file; the server
  serves exactly what's in it. (Researched alternatives — pure clock, clock+override — rejected.)
- **`obs-urlsource` over browser-source / websocket-push / read-from-file:** it's literally
  the "OBS does a REST call to a Python server" model the owner pictured, renders with native
  OBS text styling (the owner is OBS-fluent and didn't want to style a web page), and is the
  least custom code on our side (Flask just serves JSON — no websocket reconnect loop, no
  atomic file-writing, no ~1 s file-poll lag). Trade-off accepted: one plugin per PC. The
  built-in OBS text source *cannot* fetch a URL on its own — confirmed by web research
  (sources: obsproject.com forums on text/URL sources; the `royshil/obs-urlsource` plugin).

## Architecture

```
data/schedule.json  ──(hot-reload on save)──►  Flask (live/app.py)  ──REST JSON──►  obs-urlsource ×N
 (operator edits           re-read on mtime      /field/A  /field/B0  /field/B1      (native OBS text
  one pointer/field)        change               /health                              sources, per field)
                                                                                      over the styled
                                                                                      NextMatch / bg layer
```

One Flask process on **one machine**; every OBS PC pulls from it over the LAN.

## The one file — `live/data/schedule.json`

Full schedule (seeded once from the owner's markdown schedule — see Import) + a tiny live
section the operator edits during the stream:

```jsonc
{
  "schedule": [
    {"id": "thu-A-1", "day": "2026-07-02", "division": "A", "field": "A", "time": "08:30",
     "label": "G1", "teamA": "TIGERs", "teamB": "Ri-one"},
    {"id": "thu-A-2", "day": "2026-07-02", "division": "A", "field": "A", "time": "10:00",
     "label": "G2", "teamA": "ZJUNLict", "teamB": "LUHBots"}
    // …all matches; playoffs seeded with bracket codes until teams are known…
  ],
  "live": {
    "A":  {"currentId": "thu-A-1"},   // ◄── operator bumps this as matches finish
    "B0": {"currentId": "thu-B0-1"},
    "B1": {"currentId": "thu-B1-1"}
  }
}
```

- **Divisions:** Field A = **Division A** (8 teams, groups G1–G2); Fields B0 + B1 = **Division B**
  (14 teams, groups G1–G4) run in parallel. Critically, **group labels and playoff codes repeat
  across divisions** (`G1`, `G2`, `G1.2`, `G2.3`, … exist in *both* and mean different teams), so
  every match carries a `division` and is keyed by division/field — never deduped by label alone.
  Divisions don't mix. `division` is derivable from `field` (A→A, B0/B1→B) but stored explicitly
  for labelling (cards can show "DIVISION A / B").
- The server derives **`now`** = the match with `currentId`, **`next`** = the next match on
  that **same field** by `(day, time)`, and the **countdown** from `next`'s scheduled datetime.
- Optional per-field overrides for when reality diverges: `live.A.nextStartsAt` (explicit
  target time for the countdown) and/or `live.A.nextId` (force a specific next match).
- **Times are venue-local (KST).** The server uses its local wall-clock; the stream PCs run
  on venue time, so no timezone math. (Documented assumption, not a config knob.)

## Server — `live/app.py` + `live/schedule_logic.py`

- **`schedule_logic.py` (pure, unit-tested):** `resolve(data, field, now_dt) -> dict`. No I/O,
  no Flask — given the loaded data, a field, and "now", returns the response below. This is the
  only tested layer (mirrors the project's "test the logic, eyeball the visuals" convention).
- **`app.py` (thin Flask):** loads `schedule.json`, **re-reads it when its mtime changes**
  (hot-reload, no restart), exposes the routes, calls `resolve`. Host/port from config/env
  (`HOST=0.0.0.0`, `PORT=8000` defaults) so it binds on the LAN.

Response (`GET /field/A`) — includes both raw fields and **ready-to-render strings** so the
obs-urlsource extraction is a trivial JSON-pointer pick:

```json
{
  "field": "A",
  "now":  {"label": "G1", "teamA": "TIGERs", "teamB": "Ri-one", "time": "08:30",
           "matchup": "TIGERs vs Ri-one"},
  "next": {"label": "G2", "teamA": "ZJUNlict", "teamB": "luhbots", "time": "10:00",
           "matchup": "ZJUNlict vs luhbots"},
  "secondsUntilNext": 5400,
  "countdown": "1:30:00"
}
```

- `countdown` formats adaptively (`MM:SS` under an hour, `H:MM:SS` over). If `next` is overdue
  or absent, `secondsUntilNext` clamps to `0` and `countdown` to `"0:00"` (overlay never shows
  a negative). If the field has no more matches, `next` is `null`.
- Routes: `/field/<A|B0|B1>`, `/health`. Unknown field → 404; `currentId` not found → 422 with
  a clear message (so a typo in the file is obvious, not a silent blank).

## OBS wiring (obs-urlsource)

Per field, add `obs-urlsource` text source(s) pointed at `http://<server-ip>:8000/field/A`,
refresh ~1–2 s, extracting the JSON field you want (`now.matchup`, `next.matchup`, `countdown`)
via JSON pointer; render with the chosen brand font. Place them over the existing `NextMatch`
slot / lower-third. The plugin's output templating can also combine fields into one string
(e.g. `NEXT: {next.matchup} — {countdown}`).

## Distribution to multiple PCs

OBS **Scene Collection** export/import (JSON) carries the scenes, the urlsource URLs, text
styling, and image/media sources; **Profile** export carries encoder/output settings. Build
once, export, import per PC. For the import to "just work" on each machine:

1. **`obs-urlsource` installed** on every PC (collection references the plugin source type).
2. **Server addressed by a stable LAN IP/hostname**, *not* `localhost`, baked into the
   urlsource URLs — so every PC pulls from the one shared server/file.
3. **Assets at an identical absolute path** on every PC (OBS stores absolute paths for
   image/media sources): keep `next-match.png` / `breathing-background.mp4` / `standby.mp4`
   in the same folder everywhere. Install the **brand font** on every PC or text falls back.

The `live/README.md` ships a **per-PC setup checklist** covering exactly these.

## Data import — `live/import_schedule.py`

Converts the owner's markdown schedule (`# Day` → `## Field` → `### time | group | teamA |
teamB`) into `data/schedule.json`, assigning stable `id`s (`<day>-<field>-<n>`, unique across
divisions), deriving `division` from the field, and zero-padding times. Team-name **spelling
follows the owner's markdown** (their typed version is canonical); the importer **validates as
it goes** — round-robin completeness per division+group and near-duplicate team names — and
flags anomalies. (This caught the `TurtleRabbot`→`TurtleRabbit` typo and confirmed 22 teams /
all groups complete.) Playoff entries without real teams import with their bracket codes as
placeholders.

## Project layout (new)

```
live/
  app.py                       # Flask: routes, mtime hot-reload, serves JSON
  schedule_logic.py            # PURE resolve(data, field, now) -> dict   [tested]
  import_schedule.py           # markdown schedule -> data/schedule.json
  data/schedule.json           # the one file the operator edits
  tests/test_schedule_logic.py # pytest: now/next/countdown/edge cases
  requirements.txt             # flask
  README.md                    # run + per-PC OBS setup checklist
```

## Testing

`schedule_logic.resolve` is pure and pytest-covered: now/next selection, countdown formatting
(under/over an hour), overdue → clamp to 0, last-match → `next: null`, unknown field, bad
`currentId`. Flask routes are thin wrappers (smoke-checked). OBS rendering is verified
observationally in OBS, per project convention.

## Out of scope (deferred)

- **No browser source, no HTML/CSS overlay** — explicitly rejected in favour of native text.
- **No clock-based auto-advance and no automatic scene switching** — the operator drives the
  pointer; the server never decides what's "live" on its own.
- **No automatic resolution of playoff bracket codes to teams** — operator fills those in the
  file when known.
- **No auth/TLS** — trusted LAN; the server serves read-only public schedule data.
- **Match-intro card and in-match score bug** — future graphics that can reuse these same
  endpoints; not built here.
- **Python install:** `pip install -r live/requirements.txt`.
