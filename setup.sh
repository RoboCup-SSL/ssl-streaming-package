#!/usr/bin/env bash
# One-time setup for a field PC. Installs Python deps and the MediaMTX binary,
# and reports any missing prerequisites. Safe to re-run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

say()  { printf '%s\n' "$*"; }
warn() { printf '[!!]   %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

# A freshly-installed uv (and other user tools) land here; make sure they're findable.
export PATH="$HOME/.local/bin:$PATH"

# --- prerequisites this script itself needs ---
for tool in curl tar; do
  have "$tool" || { warn "'$tool' is required but not installed — install it and re-run."; exit 1; }
done

# --- uv ---
if have uv; then
  say "[ok]   uv $(uv --version | awk '{print $2}')"
else
  say "[..]   installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# --- Python deps ---
say "[..]   uv sync (services workspace)"
# Build the venv fresh. --all-packages installs every workspace member; the clean rebuild
# avoids editable-install corruption that a re-sync over an existing venv can cause on some
# uv versions. run.sh never re-syncs, so this is the single source of truth for the env.
( cd services && rm -rf .venv && uv sync --all-packages >/dev/null )
say "[ok]   python deps installed"

# --- MediaMTX binary (per platform) ---
# Fail soft: any problem here prints an actionable message and the script continues to the
# prerequisite report, rather than aborting cryptically.
install_mediamtx() {
  if [ -x bin/mediamtx ]; then say "[ok]   mediamtx (bin/mediamtx)"; return 0; fi

  local os arch mtx_os mtx_arch
  os=$(uname -s); arch=$(uname -m)
  case "$os" in
    Linux)  mtx_os=linux ;;
    Darwin) mtx_os=darwin ;;
    MINGW*|MSYS*|CYGWIN*) mtx_os=windows ;;
    *) warn "unknown OS '$os' — download MediaMTX into bin/ yourself"; return 0 ;;
  esac
  case "$arch" in
    x86_64|amd64)  mtx_arch=amd64 ;;
    aarch64|arm64) mtx_arch=arm64 ;;
    armv7l)        mtx_arch=armv7 ;;
    *) warn "unknown arch '$arch' — download MediaMTX into bin/ yourself"; return 0 ;;
  esac

  local ver
  if [ -n "${MEDIAMTX_VERSION:-}" ]; then
    ver=$MEDIAMTX_VERSION
  else
    say "[..]   querying latest MediaMTX version"
    local api
    # Capture the whole response first — piping curl into `grep -m1` makes grep close the
    # pipe early, which makes curl fail with "write error" (exit 23).
    if ! api=$(curl -fsSL https://api.github.com/repos/bluenviron/mediamtx/releases/latest); then
      warn "couldn't reach the GitHub API. Set MEDIAMTX_VERSION=vX.Y.Z and re-run, or download MediaMTX into bin/ manually."
      return 0
    fi
    ver=$(printf '%s\n' "$api" | grep -m1 '"tag_name"' | sed -E 's/.*"(v[^"]+)".*/\1/' || true)
  fi
  if [ -z "$ver" ]; then
    warn "could not determine the MediaMTX version. Set MEDIAMTX_VERSION=vX.Y.Z and re-run."
    return 0
  fi

  local ext=tar.gz binname=mediamtx
  if [ "$mtx_os" = windows ]; then ext=zip; binname=mediamtx.exe; fi
  local asset="mediamtx_${ver}_${mtx_os}_${mtx_arch}.${ext}"
  local url="https://github.com/bluenviron/mediamtx/releases/download/${ver}/${asset}"
  say "[..]   downloading MediaMTX ${ver} (${mtx_os}/${mtx_arch})"
  say "       ${url}"

  mkdir -p bin
  local tmp; tmp=$(mktemp -d)
  if ! curl -fSL --progress-bar "$url" -o "$tmp/$asset"; then
    warn "download failed (see URL above). If the version is wrong, set MEDIAMTX_VERSION; or download manually into bin/."
    rm -rf "$tmp"; return 0
  fi
  if [ "$ext" = zip ]; then unzip -o -q "$tmp/$asset" -d "$tmp"; else tar -xzf "$tmp/$asset" -C "$tmp"; fi
  if [ ! -f "$tmp/$binname" ]; then
    warn "the archive didn't contain '$binname' — extract it into bin/ manually."
    rm -rf "$tmp"; return 0
  fi
  mv "$tmp/$binname" bin/mediamtx
  chmod +x bin/mediamtx
  rm -rf "$tmp"
  say "[ok]   mediamtx ${ver} -> bin/mediamtx"
}
install_mediamtx

# --- fixed media path for OBS ---
# Create it now (not just in run.sh) so OBS scenes can be built before the first run. The OBS
# scene collection references media via /var/tmp/ssl-streaming-package/... so the same scenes.json
# works on every field PC regardless of where the repo was cloned or the username. /var/tmp
# survives reboots (FHS). NOTE: run.sh duplicates this block — keep them in sync if you change it.
MEDIA_LINK=/var/tmp/ssl-streaming-package
if [ -L "$MEDIA_LINK" ] || [ ! -e "$MEDIA_LINK" ]; then
  # rm + ln (not `ln -sfn`, whose -n differs on GNU vs BSD/macOS) so re-runs replace
  # the symlink instead of nesting a link inside it.
  rm -f "$MEDIA_LINK"
  ln -s "$ROOT" "$MEDIA_LINK"
  say "[ok]   media path $MEDIA_LINK -> $ROOT"
else
  warn "$MEDIA_LINK exists and is not a symlink — OBS media paths may not resolve"
fi

# --- runtime prerequisites the deployer must have ---
have ffmpeg && say "[ok]   ffmpeg" || say "[!!]   ffmpeg MISSING — install it (needed for USB/MPEG-TS cameras)"
have obs    && say "[ok]   obs"    || say "[!!]   OBS not on PATH — install OBS 28+ (launched manually)"

say ""
say "Next: cp field.toml.example field.toml, edit it, then ./run.sh"
