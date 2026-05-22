#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [[ -n "${TEST_DATABASE_URL:-}" || -n "${DATABASE_URL:-}" ]]; then
  python -m migrations.run
fi

python -m pytest -q
