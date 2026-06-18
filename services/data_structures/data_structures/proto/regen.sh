#!/usr/bin/env bash
# Regenerate the protobuf bindings. Run from the proto/ dir: ./regen.sh
set -euo pipefail
cd "$(dirname "$0")"
uv run python -m grpc_tools.protoc -I. --python_out=. ssl_gc_referee.proto
