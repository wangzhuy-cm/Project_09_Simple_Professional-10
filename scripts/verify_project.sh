#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi
"$PYTHON" -m compileall -q app.py src ui tests
"$PYTHON" -m pip check
"$PYTHON" -m pytest -q
