#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
export PYTHONPYCACHEPREFIX="$scratch/pycache"
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins tests
if [[ -x /usr/lib/qt6/bin/qmllint ]]; then
  /usr/lib/qt6/bin/qmllint --ignore-settings --max-warnings -1 \
    --import disable --unqualified disable --missing-property disable \
    --unresolved-type disable --missing-type disable --required disable \
    --incompatible-type disable --syntax error --syntax.duplicate-ids error \
    --duplicated-name error --duplicate-import error --alias-cycle error \
    --inheritance-cycle error --unterminated-case error \
    --var-used-before-declaration error --eval error --with error \
    plugins/*/*.qml
fi
if command -v shellcheck >/dev/null; then
  shellcheck tools/check.sh
fi
git diff --check
