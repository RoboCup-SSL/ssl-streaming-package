#!/usr/bin/env bash
# One-time setup for a field PC. Installs Python deps and the MediaMTX binary,
# and reports any missing prerequisites. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

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
( cd services && uv sync >/dev/null )
say "[ok]   python deps installed"

# --- MediaMTX binary (per platform) ---
if [ -x bin/mediamtx ]; then
  say "[ok]   mediamtx (bin/mediamtx)"
else
  os=$(uname -s); arch=$(uname -m)
  case "$os" in
    Linux)  mtx_os=linux ;;
    Darwin) mtx_os=darwin ;;
    MINGW*|MSYS*|CYGWIN*) mtx_os=windows ;;
    *) say "[!!]   unknown OS '$os' — download MediaMTX manually into bin/"; mtx_os= ;;
  esac
  case "$arch" in
    x86_64|amd64) mtx_arch=amd64 ;;
    aarch64|arm64) mtx_arch=arm64 ;;
    armv7l) mtx_arch=armv7 ;;
    *) say "[!!]   unknown arch '$arch' — download MediaMTX manually into bin/"; mtx_arch= ;;
  esac
  if [ -n "$mtx_os" ] && [ -n "$mtx_arch" ]; then
    ver=${MEDIAMTX_VERSION:-$(curl -sSL https://api.github.com/repos/bluenviron/mediamtx/releases/latest \
      | grep -m1 '"tag_name"' | sed -E 's/.*"(v[^"]+)".*/\1/')}
    ext=tar.gz; [ "$mtx_os" = windows ] && ext=zip
    asset="mediamtx_${ver}_${mtx_os}_${mtx_arch}.${ext}"
    url="https://github.com/bluenviron/mediamtx/releases/download/${ver}/${asset}"
    say "[..]   downloading MediaMTX ${ver} (${mtx_os}/${mtx_arch})"
    mkdir -p bin
    tmp=$(mktemp -d)
    curl -sSL "$url" -o "$tmp/$asset"
    if [ "$ext" = zip ]; then unzip -o -q "$tmp/$asset" -d "$tmp"; else tar -xzf "$tmp/$asset" -C "$tmp"; fi
    mv "$tmp/mediamtx" bin/mediamtx
    chmod +x bin/mediamtx
    rm -rf "$tmp"
    say "[ok]   mediamtx -> bin/mediamtx"
  fi
fi

# --- runtime prerequisites the deployer must have ---
have ffmpeg && say "[ok]   ffmpeg" || say "[!!]   ffmpeg MISSING — install it (needed for USB/MPEG-TS cameras)"
have obs    && say "[ok]   obs"    || say "[!!]   OBS not on PATH — install OBS 28+ (launched manually)"

say ""
say "Next: cp field.toml.example field.toml, edit it, then ./run.sh"
