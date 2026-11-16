#!/usr/bin/env bash
# Checkpoint: tests + lint + format + types. Usage: ./check.sh [pytest args]
set -e
cd "$(dirname "$0")"
uv run pytest -q "$@" > .superpowers/last_test.log 2>&1 || { tail -40 .superpowers/last_test.log; exit 1; }
tail -2 .superpowers/last_test.log
uv run ruff check . --fix -q || true
uv run python -m black -q .
uv run ruff check . -q
if ! out=$(uv run python -m mypy src --no-error-summary 2>&1); then
  if echo "$out" | grep -q "Application Control policy"; then
    echo "WARNING: mypy skipped - Windows Application Control blocked its compiled files"
  else
    echo "$out"; exit 1
  fi
fi
echo CHECK_OK
