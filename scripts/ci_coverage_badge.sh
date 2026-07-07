#!/usr/bin/env bash
# pytest coverage → docs/badges/coverage.svg (real % badge).
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=. python3 -m pytest tests/ --cov=helios --cov-report=json:coverage/coverage.json -q
python3 scripts/generate_coverage_badge.py coverage/coverage.json docs/badges/coverage.svg
if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  git diff --quiet docs/badges/coverage.svg || {
    echo "docs/badges/coverage.svg drift — regenerate in monorepo and re-mirror" >&2
    exit 1
  }
fi
