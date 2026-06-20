# Deployment UX — design

Date: 2026-06-19
Status: approved (brainstorm), pre-implementation

## Goal

Turn the repo from a developer checkout into a **clone-and-run field deployment**: download,
edit one root config, run two scripts, and the field PC is streaming-ready — replicated to
three fields by copying the repo and changing only the camera list. This is README feature 5
(package deployment), pulled forward by the one-week, three-field tournament deadline.

## Hirer: the field deployer

A volunteer/organizer setting up a field's streaming PC, on or just before tournament day.
Linux- and programming-literate, but **not** a Python/uv/OBS/MediaMTX expert. Time-pressured,
possibly flaky venue internet, doing the same setup on three fields.

### Jobs
- **Functional:** make a field PC stream-ready end to end (cameras → MediaMTX → OBS look →
  live match data → YouTube) before first kickoff; replicate to fields 2 and 3; recover fast
  if something breaks mid-day.
- **Social:** not be the field with the broken/janky stream; look competent to organizers.
- **Emotional:** confidence it will "just work"; low tournament-morning anxiety.

### Pains (ranked)
1. Assembling many prerequisites (uv, OBS, MediaMTX, ffmpeg, fonts) under time pressure.
2. Config scattered across service dirs; multiple per-service commands; working-directory
   gotchas (the logos-cwd bug is exactly this class).
3. Replicating to three fields is error-prone copy-work.
4. No up-front signal of misconfiguration before going live.

### Gains that drive adoption
One root config file; one setup command; one run command; copy-to-replicate; a preflight that
flags problems before air.

## User stories

1. As a field deployer, I want **one documented setup command**, so I'm not hunting tool
   versions on tournament morning.
2. As a field deployer, I want **all field settings in one obvious file**, so I'm not editing
   configs scattered across folders.
3. As a field deployer, I want **one command to start MediaMTX + live-data**, so I don't
   memorize per-service invocations or hit cwd quirks.
4. As the league organizer, I want to **bring up fields 2 and 3 by copying field 1** and
   changing only the camera list.
5. As a field deployer, I want an **up-front check** that flags misconfig (missing prereq,
   wrong OBS source name, camera offline) before I go live.
6. As a field deployer, I want **clear prerequisites** (and what's missing) when something
   isn't installed.

## Design

### Single root config

Move the canonical per-field config to the **repo root**: `field.toml` (one per field PC),
with `field.toml.example` alongside. All tools read it. `field.toml` stays git-ignored (holds
the OBS password); `field.toml.example` is the template. This is the single thing a deployer
edits, and the only per-field difference when replicating.

Consequence — **asset paths must not depend on cwd or config location.** Specifically,
`obs-live-data`'s `logos_dir` default must resolve to the **bundled package logos** (via the
package location, not a path relative to the moved config). An explicit `logos_dir`/`stage_dir`
still overrides. This removes the relative-path fragility that the root move would otherwise
introduce.

### `setup.sh` (repo root)

Idempotent. Run once per field PC. Steps:
- Ensure `uv` is available (install via the official installer if missing).
- `uv sync` the `services/` workspace (Python deps).
- Check `OBS`, `mediamtx`, `ffmpeg` are on PATH; if `mediamtx` is missing, fetch the binary
  into `./bin/` from its GitHub release.
- Print a clear status line per prerequisite (present / installed / **missing — do X**).

Installs are the deployer's to run (matches the project's manual-install policy); `setup.sh`
is a script *they* execute, not something committed code runs implicitly.

### `run.sh` (repo root)

One command to bring the field up. Steps:
- Generate `mediamtx.yml` from the root `field.toml` (via `mediamtx-controller`).
- Start MediaMTX with that config in the background.
- Start `obs-live-data` against the root `field.toml`.
- On exit (Ctrl-C), stop the background MediaMTX (a `trap`, so no orphan processes).
- Print the next manual step: import the OBS scene collection (once it exists) and start
  streaming. OBS itself is launched by the deployer (it's a GUI app).

This is a launcher, not in-app process supervision — it keeps the "no weird process
management" preference: each component still runs as its own normal process.

### Top-level README quickstart

The repo root README gets a Quickstart that is the happy path verbatim:

```
git clone … && cd ssl-streaming-package
./setup.sh
cp field.toml.example field.toml      # edit cameras, OBS password, source names
./run.sh
# then import the OBS scene collection and go live
```

Plus a one-paragraph "replicate to another field: copy the repo, edit `[cameras]`."

### Preflight (story 5)

`obs-live-data` already has an OBS-input preflight (in the demo). Generalize it so the real app
also reports, at startup: prerequisites found, OBS connected, configured source/image names
that don't exist in OBS, and camera paths that aren't publishing yet. Non-fatal warnings, printed
before going live. (The deeper version can live in `run.sh` as a combined check.)

## Scope

In scope: root `field.toml` move + the `logos_dir` default fix; `setup.sh`; `run.sh`;
root README quickstart; generalized preflight.

Out of scope (separate, later): the OBS scene-collection design/export itself (the operator
designs it in OBS — option 1), and the graphics-asset path-fixup importer for that collection.
Windows support.

## Testing

- `obs-live-data` logo-dir default resolves to the bundled package dir regardless of cwd
  (unit test with the package path).
- `setup.sh` / `run.sh` are shell glue verified by running them on this box (no unit tests);
  the Python pieces they call are already covered.
- Re-run the full `uv run pytest` suite green after the config-path changes.
