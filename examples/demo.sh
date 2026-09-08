#!/usr/bin/env bash
# Tiny demo: seal a deterministic command with a tracked input file.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
printf 'hello runseal\n' > /tmp/runseal-demo-input.txt
python -m runseal run --label demo --track /tmp/runseal-demo-input.txt --store-output -- \
  python -c "print(open('/tmp/runseal-demo-input.txt').read().strip())"
