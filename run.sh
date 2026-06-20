#!/usr/bin/env bash
# Bring this field up: validate config, generate the MediaMTX config, start MediaMTX
# and obs-live-data. Ctrl-C (or any exit) stops everything it started, including the
# ffmpeg children MediaMTX spawns. OBS is launched separately (it's a GUI app).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CONFIG="$ROOT/${1:-field.toml}"
MTX_YML="$ROOT/mediamtx.yml"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

[ -f "$CONFIG" ] || die "$CONFIG not found — cp field.toml.example field.toml and edit it"
[ -x "$ROOT/bin/mediamtx" ] || die "bin/mediamtx not found — run ./setup.sh first"

# --- config sanity (fail fast, reusing tested code) ---
# Cameras + TOML validity: generating the MediaMTX config raises on bad camera names/descriptors.
( cd services && uv run --package mediamtx-controller python -m mediamtx_controller "$CONFIG" "$MTX_YML" ) \
  || die "invalid [cameras] in field.toml (see message above)"
# OBS/field/schedule structure: loading FieldConfig raises on missing/malformed sections.
( cd services && uv run --package configuration python -c \
  "from configuration.appconfig import FieldConfig; FieldConfig.load_from_file('$CONFIG')" ) \
  || die "invalid field.toml: check [field], [obs], [schedule] (see message above)"
echo "config OK"

# --- start MediaMTX; on exit kill it AND the ffmpeg children it spawns ---
# No setsid: $! is genuinely mediamtx's pid. ffmpeg processes are its direct children,
# so pkill -P reaps them; killing mediamtx too. (On Ctrl-C the terminal also SIGINTs the
# whole foreground group, so this is belt-and-suspenders.)
"$ROOT/bin/mediamtx" "$MTX_YML" &
MTX_PID=$!
cleanup() {
  pkill -TERM -P "$MTX_PID" 2>/dev/null || true
  kill -TERM "$MTX_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
echo "MediaMTX started (pid $MTX_PID)"

echo "Next: import the OBS scene collection, launch OBS, and go live."
echo "Running obs-live-data — Ctrl-C to stop everything."

# --- obs-live-data in the foreground; on Ctrl-C the trap tears MediaMTX down ---
( cd services && uv run --package obs-live-data python -m obs_live_data "$CONFIG" )
