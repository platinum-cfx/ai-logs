#!/usr/bin/env bash
# Watches the two Phase 1 P2 builds; when BOTH are green, packages v0.7 + v0.4
# and swaps the release assets. All output -> /var/tmp/phase1-pack/watcher.log
set -u
T="${GH_TOKEN:?Set GH_TOKEN}"
API="https://api.github.com/repos/platinum-cfx/NSM-FIVEM"
SRUN=38682705476   # fxserver (retry on 4951fff - monitor banner fix)
CRUN=38683776474   # fivem (retry on 9747097 - patcher syntax fix)
LOG=/var/tmp/phase1-pack/watcher.log
mkdir -p /var/tmp/phase1-pack

status_of() {
  curl -s -m 30 -H "Authorization: token $T" "$API/actions/runs/$1" | \
    python3 -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d.get('conclusion') or '-')"
}

while true; do
  S=$(status_of $SRUN)
  C=$(status_of $CRUN)
  echo "$(date -u '+%H:%M:%SZ') server:[$S] client:[$C]" >> "$LOG"
  # BOTH must be completed before we decide anything
  if [[ "$S" == completed* && "$C" == completed* ]]; then
    echo "$(date -u '+%H:%M:%SZ') both completed: server:[$S] client:[$C]" >> "$LOG"
    if [[ "$S" == *success* && "$C" == *success* ]]; then
      echo "=== BOTH GREEN -> packaging + upload ===" >> "$LOG"
      python3 -u /home/user/nsm/branding/package_phase1.py \
        --server-run $SRUN --client-run $CRUN --upload >> "$LOG" 2>&1
      echo "=== watcher exit: $? ===" >> "$LOG"
      exit 0
    else
      echo "!!! A BUILD DID NOT SUCCEED - manual attention needed" >> "$LOG"
      exit 1
    fi
  fi
  sleep 300
done
