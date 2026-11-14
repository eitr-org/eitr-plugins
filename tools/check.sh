#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
export PYTHONPYCACHEPREFIX="$scratch/pycache"
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins tests
if command -v node >/dev/null; then
  node tests/test_world_clock_state.js
fi
if command -v shellcheck >/dev/null; then
  shellcheck tools/check.sh
fi
git diff --check
