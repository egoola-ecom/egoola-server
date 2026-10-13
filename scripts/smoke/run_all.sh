#!/usr/bin/env bash
# Runs every smoke suite against a running dev server and prints one summary.
# Exit code is non-zero if any check failed.
#   usage:  scripts/smoke/run_all.sh            (server on http://127.0.0.1:8000)
#           SMOKE_BASE=http://host:port scripts/smoke/run_all.sh
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
status=0
for suite in e2e admin buyer listing brand sku cms seller_onboarding seller_self public_geography seller_listing gig seller_gig; do
  echo "######## $suite"
  if [ -f "$here/${suite}_smoke.py" ]; then
    out="$(PYTHONIOENCODING=utf-8 python "$here/${suite}_smoke.py" 2>&1)"
  else
    out="$(bash "$here/${suite}_smoke.sh" 2>&1)"
  fi
  echo "$out" | grep -E "^FAIL" 
  line="$(echo "$out" | grep -E "RESULT" | tail -1)"
  echo "$suite: ${line:-NO RESULT LINE (script crashed?)}"
  echo "$line" | grep -Eq " 0 failed" || status=1
done
exit $status
