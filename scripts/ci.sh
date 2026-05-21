#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pytest -q tests/test_domain/test_reducers.py tests/test_api/test_commands.py tests/test_worker/test_outbox_claiming.py
