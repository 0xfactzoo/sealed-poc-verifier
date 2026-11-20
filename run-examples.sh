#!/usr/bin/env bash
# Run both bundled examples and save evidence JSONs.
# Exit 0 only if vulnerable -> REPRODUCED and fixed -> NOT_REPRODUCED.
set -u
cd "$(dirname "$0")"

echo "== 1. Vulnerable target (expect REPRODUCED) =="
python3 src/verifier.py \
  --poc examples/vulnerable/ReentrancyPoC.t.sol \
  --target examples/vulnerable/VulnerableVault.sol \
  --out examples/evidence-vulnerable.json
rc1=$?
echo "exit: $rc1"

echo
echo "== 2. Fixed target (expect NOT_REPRODUCED) =="
python3 src/verifier.py \
  --poc examples/vulnerable/ReentrancyPoC.t.sol \
  --target examples/fixed/FixedVault.sol \
  --out examples/evidence-fixed.json
rc2=$?
echo "exit: $rc2"

echo
echo "== Verdicts =="
python3 -c "import json; print('vulnerable:', json.load(open('examples/evidence-vulnerable.json'))['verdict']); print('fixed:     ', json.load(open('examples/evidence-fixed.json'))['verdict'])"
