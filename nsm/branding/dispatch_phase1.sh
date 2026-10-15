#!/usr/bin/env bash
# Re-dispatch the two P2 builds on the current a1-rebrand tip (after billing is fixed).
# Usage: bash dispatch_phase1.sh
set -e
T="${GH_TOKEN:?Set GH_TOKEN}"
API="https://api.github.com/repos/platinum-cfx/NSM-FIVEM"
tip=$(curl -s -H "Authorization: token $T" "$API/git/ref/heads/a1-rebrand" | python3 -c "import json,sys;print(json.load(sys.stdin)['object']['sha'])")
echo "a1-rebrand tip: $tip"
for product in fxserver fivem; do
  code=$(curl -s -o /tmp/disp.json -w "%{http_code}" -X POST \
    -H "Authorization: token $T" -H "Accept: application/vnd.github+json" \
    "$API/actions/workflows/383704415/dispatches" \
    -d "{\"ref\":\"a1-rebrand\",\"inputs\":{\"product\":\"$product\"}}")
  echo "$product dispatch: HTTP $code"
  [ "$code" = "204" ] || { cat /tmp/disp.json; exit 1; }
done
sleep 20
curl -s -H "Authorization: token $T" "$API/actions/runs?per_page=2" | python3 -c "
import json,sys
for r in json.load(sys.stdin)['workflow_runs']:
    print(r['id'], r['head_sha'][:12], r['status'], r.get('conclusion'))"
echo
echo "Then watch: fxserver ~70 min, fivem ~110 min."
echo "When green:  python3 /home/user/nsm/branding/package_phase1.py --server-run <id> --client-run <id> --upload"
