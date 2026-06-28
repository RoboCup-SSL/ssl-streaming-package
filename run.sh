#!/usr/bin/env bash
# Bring this field up: validate config, generate the MediaMTX config, start MediaMTX
# and obs-live-data. Ctrl-C (or any exit) stops everything it started, including the
# ffmpeg children MediaMTX spawns. OBS is launched separately (it's a GUI app).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CONFIG="$ROOT/${1:-field.toml}"
MTX_YML="$ROOT/mediamtx.yml"

# Find a uv that setup.sh may have just installed into ~/.local/bin.
export PATH="$HOME/.local/bin:$PATH"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v uv >/dev/null 2>&1 || die "uv not found — run ./setup.sh first (it installs uv)"
[ -f "$CONFIG" ] || die "$CONFIG not found — run: cp field.toml.example field.toml  (then edit it)"
[ -x "$ROOT/bin/mediamtx" ] || die "bin/mediamtx not found — run ./setup.sh first"

# Use the venv that setup.sh built, and call its interpreter directly. We deliberately do NOT
# `uv sync` here: a re-sync over an existing venv can corrupt editable installs on some uv
# versions (it deleted workspace members on macOS). setup.sh owns building the env, once.
PY="$ROOT/services/.venv/bin/python"
{ [ -x "$PY" ] && "$PY" -c "import mediamtx_controller, configuration, obs_live_data" >/dev/null 2>&1; } \
  || die "Python environment not ready — run ./setup.sh first"

# --- config sanity (fail fast, reusing tested code) ---
# Cameras + TOML validity: generating the MediaMTX config raises on bad camera names/descriptors.
"$PY" -m mediamtx_controller "$CONFIG" "$MTX_YML" \
  || die "invalid [cameras] in field.toml (see message above)"
# OBS/field/schedule structure: loading FieldConfig raises on missing/malformed sections.
"$PY" -c "from configuration.appconfig import FieldConfig; FieldConfig.load_from_file('$CONFIG')" \
  || die "invalid field.toml: check [field], [obs], [schedule] (see message above)"
echo "config OK"

# --- non-fatal nudges for an un-edited config (noob safety net) ---
"$PY" -m configuration.checks "$CONFIG" || true

# --- fixed media path for OBS ---
# The OBS scene collection references media via /var/tmp/ssl-streaming/... so the same
# scenes.json works on every field PC regardless of where the repo was cloned or the
# username. /var/tmp survives reboots (FHS); we (re)create the symlink each run anyway.
# NOTE: setup.sh duplicates this block so the link exists before the first run — keep them
# in sync if you change it.
MEDIA_LINK=/var/tmp/ssl-streaming
if [ -L "$MEDIA_LINK" ] || [ ! -e "$MEDIA_LINK" ]; then
  # rm + ln (not `ln -sfn`, whose -n differs on GNU vs BSD/macOS) so re-runs replace
  # the symlink instead of nesting a link inside it.
  rm -f "$MEDIA_LINK"
  ln -s "$ROOT" "$MEDIA_LINK"
else
  printf '[warn] %s exists and is not a symlink — OBS media paths may not resolve\n' "$MEDIA_LINK" >&2
fi

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
"$PY" -m obs_live_data "$CONFIG"
