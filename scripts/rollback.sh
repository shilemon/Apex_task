#!/usr/bin/env bash
# Usage: ./scripts/rollback.sh
# Switches traffic back to the previous release (the other, stopped slot) without rebuilding.
# The bad release stays in its stopped slot so it can be inspected.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

[ -f "$STATE" ] || { echo "No release state found (.release/state.env). Nothing to roll back."; exit 1; }
load_state
[ -n "$ACTIVE" ] || { echo "No active release recorded."; exit 1; }

if [ "$ACTIVE" = blue ]; then TARGET=green; TARGET_TAG="$GREEN_TAG"; else TARGET=blue; TARGET_TAG="$BLUE_TAG"; fi
[ "$TARGET_TAG" != none ] || { echo "No previous release recorded. Redeploy an older tag with deploy.sh."; exit 1; }
docker image inspect "apex-ops-api:$TARGET_TAG" >/dev/null 2>&1 \
  || { echo "Image apex-ops-api:$TARGET_TAG not found locally. Redeploy that tag with deploy.sh."; exit 1; }

export BLUE_TAG GREEN_TAG
echo "==> Rolling back: slot $ACTIVE -> slot $TARGET (version $TARGET_TAG)"
docker compose up -d --wait --no-build "api-$TARGET"

set_upstream "$TARGET"
if ! reload_nginx; then
  echo "!! nginx reload failed. Reverting config."
  set_upstream "$ACTIVE"
  exit 1
fi
wait_ready_via_proxy || { echo "!! Not ready through proxy. Escalate (docs/RUNBOOK.md)."; exit 1; }

sleep 5
docker compose stop "api-$ACTIVE"
save_state "$TARGET"
echo "==> Rollback complete. Live version:"
curl -s http://localhost:8000/health; echo
