#!/usr/bin/env bash
# Exécuter les sources avec le runtime Linux privé, sans modifier Python global.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export DRUM_LAB_HOME="$project_root"
export DRUM_LAB_RESOURCE_ROOT="$project_root"
export DRUM_LAB_RUNTIME_ROOT="${DRUM_LAB_RUNTIME_ROOT:-$project_root/work/linux-runtime}"
export PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$project_root"
exec "$DRUM_LAB_RUNTIME_ROOT/envs/app/bin/python" -m drum_lab.cli "$@"
