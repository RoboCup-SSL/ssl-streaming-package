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
- **Download the correct MediaMTX binary for this platform** into `./bin/`: detect OS + arch
  (`uname -s` / `uname -m` → linux/darwin/windows × amd64/arm64), map to the matching asset of
  a **pinned** MediaMTX release, fetch and extract. MediaMTX is a single static Go binary per
  platform, so this gives cross-platform support *and* keeps USB/HDMI capture working (Docker
  is avoided precisely because device passthrough breaks on Win/Mac).
- Check `OBS` and `ffmpeg` are on PATH; print a clear status line per prerequisite
  (present / installed / **missing — do X**).

Installs are the deployer's to run (matches the project's manual-install policy); `setup.sh`
is a script *they* execute, not something committed code runs implicitly.

### `run.sh` (repo root)

One command to bring the field up. Steps:
1. **Config sanity check, fail fast** before starting anything: required `field.toml` sections
   present; every `[cameras]` descriptor well-formed (`rtsp://` / `usb:` / `ts:`); `./bin/mediamtx`
   present (else "run ./setup.sh"). Generating `mediamtx.yml` already raises on bad camera
   names — reuse that. Print clear, single-line errors and exit non-zero on failure.
2. Generate `mediamtx.yml` from the root `field.toml` (via `mediamtx-controller`).
3. Start MediaMTX with that config **in its own process group**.
4. Start `obs-live-data` against the root `field.toml` (foreground).
5. Print the next manual step: import the OBS scene collection (once it exists), launch OBS,
   go live.

**Reliable teardown (hard requirement).** Stopping `run.sh` (Ctrl-C or exit) must kill
*everything it started*, including MediaMTX's ffmpeg children. Start MediaMTX in its own
process group (`setsid`) and, on `trap EXIT INT TERM`, kill the whole group (`kill -- -<pgid>`)
so no orphaned `mediamtx`/`ffmpeg` survive. Verify during testing with a `ps`/`pgrep` check
after exit — zero orphans.

This is a launcher, not in-app process supervision — each component still runs as its own
normal process; the launcher just owns clean startup and teardown.

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

Out of scope (separate, later):
- The OBS scene-collection design/export itself (the operator designs it in OBS — option 1),
  and the graphics-asset path-fixup importer for that collection.
- **Live schedule push** (next-match / countdown text to OBS) — the engine exists
  (`import_schedule.py`, `schedule.py`, `schedule.json`) but wiring the periodic push is
  deferred; likely wired alongside some OBS Lua scripts Emiel wants to integrate later.
- An interactive camera-registration TUI — editing `[cameras]` + re-running `run.sh` is the
  interface; rerunning is fine given reliable teardown.
- Full Windows support (binary download is cross-platform, but not a tested target).

## Testing

- `obs-live-data` logo-dir default resolves to the bundled package dir regardless of cwd
  (unit test with the package path).
- `setup.sh` / `run.sh` are shell glue verified by running them on this box (no unit tests);
  the Python pieces they call are already covered.
- Re-run the full `uv run pytest` suite green after the config-path changes.
