#!/usr/bin/env bash
# Usage: ./scripts/deploy.sh <version-tag>     e.g. ./scripts/deploy.sh v1.0.1
# Zero-downtime-style blue/green deploy:
#   1. build image apex-ops-api:<tag> and start it in the IDLE slot
#   2. wait until the slot's /readiness is healthy (compose --wait)
#   3. switch nginx to the new slot (graceful reload: in-flight requests finish)
#   4. stop the old slot (its image stays available for rollback)
# If anything fails before the switch, the active release is never touched.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=scripts/lib.sh
. scripts/lib.sh

NEW="${1:?usage: deploy.sh <version-tag>}"
[ -f .env ] || { echo "ERROR: .env missing. Run: cp .env.example .env and set a password."; exit 1; }

load_state
# Self-heal: if saved state says a slot is live but nginx or that slot is not actually
# running (e.g. after `make down`), forget the stale state and treat this as a first deploy.
if [ -n "$ACTIVE" ]; then
  RUNNING_NGINX="$(docker compose --profile green ps -q --status running nginx 2>/dev/null || true)"
  RUNNING_SLOT="$(docker compose --profile green ps -q --status running "api-$ACTIVE" 2>/dev/null || true)"
  if [ -z "$RUNNING_NGINX" ] || [ -z "$RUNNING_SLOT" ]; then
    echo "==> Saved state is stale (nothing live). Treating this as a first deploy."
    ACTIVE=""; BLUE_TAG=none; GREEN_TAG=none
    rm -f "$STATE"
  fi
fi
if [ -z "$ACTIVE" ]; then IDLE=blue; FIRST=1
elif [ "$ACTIVE" = blue ]; then IDLE=green; FIRST=0
else IDLE=blue; FIRST=0; fi

if [ "$IDLE" = blue ]; then BLUE_TAG="$NEW"; else GREEN_TAG="$NEW"; fi
export BLUE_TAG GREEN_TAG

echo "==> Deploying $NEW into slot '$IDLE' (active slot: ${ACTIVE:-none})"
docker compose build "api-$IDLE"

if ! docker compose up -d --wait "api-$IDLE"; then
  echo "!! api-$IDLE did not become ready. Active release left untouched."
  docker compose logs --tail 20 "api-$IDLE" || true
  docker compose stop "api-$IDLE" || true
  exit 1
fi

set_upstream "$IDLE"
if [ "$FIRST" = 1 ]; then
  docker compose up -d --wait nginx
  reload_nginx || true   # in case nginx was already running with an old upstream
else
  if ! reload_nginx; then
    echo "!! nginx reload failed. Reverting to $ACTIVE."
    set_upstream "$ACTIVE"
    docker compose stop "api-$IDLE" || true
    exit 1
  fi
fi

if ! wait_ready_via_proxy; then
  echo "!! Not ready through proxy after switch. Reverting."
  if [ -n "$ACTIVE" ]; then set_upstream "$ACTIVE"; reload_nginx || true; fi
  docker compose stop "api-$IDLE" || true
  exit 1
fi

if [ -n "$ACTIVE" ]; then
  sleep 5   # let in-flight requests on the old slot drain
  docker compose stop "api-$ACTIVE"
fi

save_state "$IDLE"
echo "==> OK: $NEW is live in slot '$IDLE'"
curl -s http://localhost:8000/health; echo
