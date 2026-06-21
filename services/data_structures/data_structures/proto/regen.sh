#!/usr/bin/env bash
# Regenerate the protobuf bindings. Run from the proto/ dir: ./regen.sh
# Uses the system protoc (grpc_tools is not a dependency here).
set -euo pipefail
cd "$(dirname "$0")"
protoc -I. --python_out=. ssl_gc_referee.proto
