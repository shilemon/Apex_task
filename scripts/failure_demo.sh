#!/usr/bin/env bash
# Failure investigation demo: stop the database, observe symptoms, recover.
# Run AFTER ./scripts/deploy.sh. Saves evidence to ./evidence/failure_demo.log
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence
OUT=evidence/failure_demo.log
: > "$OUT"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$OUT"; }

log "STEP 1 baseline"; curl -s -w ' http=%{http_code}\n' localhost:8000/readiness | tee -a "$OUT"
log "STEP 2 inject failure: stop db"; docker compose stop db 2>&1 | tee -a "$OUT"
sleep 3
log "STEP 3 symptoms (liveness vs readiness)"
curl -s -w ' http=%{http_code}\n' localhost:8000/health    | tee -a "$OUT"
curl -s -w ' http=%{http_code}\n' localhost:8000/readiness | tee -a "$OUT"
log "STEP 4a investigate: api logs"; docker compose logs --tail 5 api-blue api-green 2>&1 | tee -a "$OUT"
log "STEP 4b investigate: db_up metric"; curl -s localhost:8000/metrics | grep '^apex_db_up' | tee -a "$OUT"
log "STEP 4c investigate: container state"; docker compose ps 2>&1 | tee -a "$OUT"
log "STEP 5 recover: start db"; docker compose start db 2>&1 | tee -a "$OUT"
for _ in $(seq 1 20); do curl -fs localhost:8000/readiness >/dev/null && break; sleep 2; done
log "STEP 6 verify"; curl -s -w ' http=%{http_code}\n' localhost:8000/readiness | tee -a "$OUT"
