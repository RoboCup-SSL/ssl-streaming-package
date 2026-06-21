# obs-template

The **pre-built OBS scene collection** operators import and barely touch — the heart of MVP1's
"professional by default" look. Ships the scenes, transitions, overlays, and the assets they
reference, so a volunteer with no OBS knowledge inherits a clean broadcast.

Planned contents:
- OBS **scene-collection export** (`.json`) — scenes for field-only, field+commentator,
  commentator-fullscreen, halftime, pre/post-match.
- **Transitions** wired to the stinger WebMs rendered by [`../graphics`](../graphics/) (1.3).
- **Overlay** layers: brand frames/banners (1.5), the commentator-cam layout (1.2), scene
  fades (1.1).
- Live match overlay: Text and Image sources fed by [`../services/obs-live-data`](../services/obs-live-data/)
  over obs-websocket (2.2). See **Live overlay source names** below.
- Setup notes / per-PC import checklist.

See the operator-facing instructions in [`../docs/handbook`](../docs/handbook/).

## Live overlay source names

`obs-live-data` pushes each match field to an OBS source **by name** — there is no mapping
file. To show a field, create an OBS source named **exactly** as below. Anything you don't
create is simply not shown (the push is a harmless no-op), so build only what your scene needs.

All of these are **Text (GDI+ / FreeType2)** sources except the two logos, which are **Image**
sources. Times are `MM:SS` (negative in overtime).

**Per team** (`blue_*` and `yellow_*`):

| Source name | Shows |
|---|---|
| `blue_name` / `yellow_name` | team name |
| `blue_score` / `yellow_score` | score |
| `blue_yellow_cards` / `yellow_yellow_cards` | yellow-card count |
| `blue_red_cards` / `yellow_red_cards` | red-card count |
| `blue_card_time_1`, `blue_card_time_2` / `yellow_card_time_1`, `yellow_card_time_2` | active yellow-card timers (blank when fewer than two) |
| `blue_substitution` / `yellow_substitution` | `Substitution Active (0:18)` / `Substitution Requested` / blank |
| `blue_logo` / `yellow_logo` | **Image** source — team logo |

**Center / match:**

| Source name | Shows |
|---|---|
| `stage` | stage label, e.g. `1st Half`, `Half Time`, `Match finished` |
| `stage_time` | stage clock, e.g. `04:21` |
| `game_state` | coarse play state, e.g. `Game is Running`, `Game is Halted`, `Game is Stopped`, `Timeout`, `Ball Placement` |
| `command` | detailed command incl. team + inline time, e.g. `Free Kick for Blue`, `Ball Placement for Blue (00:08)`, `Timeout for Yellow (01:23)`, `Halt` |
| `next_command` | `Next: Kickoff for Yellow` (blank when none) |

> Tip: run `uv run python -m obs_live_data.demo field.toml` — it prints OBS's current input
> names and plays a scripted match, so you can confirm your sources are named correctly.
>
> To test against a **real** match, replay an official SSL gamelog:
> `uv run python -m obs_live_data.demo_gamelog <gamelog.log.gz> field.toml [speed]`
> (`speed` is a playback multiplier, e.g. `5` for 5×).

## Status

**Scaffold + live-overlay contract.** The data side (obs-live-data) pushes all the source
names above. The scene collection itself is still hand-built in OBS and exported here. The
graphics it references already exist in `../graphics`.
