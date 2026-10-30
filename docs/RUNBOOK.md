# Runbook — Apex Operations API

Release details: `RELEASE.md`. Monitoring: `MONITORING.md`.

## 1. Deploy
1. Confirm CI is green for the commit (and the tag, e.g. `v1.1.0`).
2. `./scripts/deploy.sh v1.1.0` — builds the image, starts it in the idle blue/green slot, waits for `/readiness`, switches nginx, stops the old slot.
3. Verify: `curl localhost:8000/health` shows the new `version`; `docker compose ps` shows `healthy`.
4. Watch logs for 5 minutes: `docker compose logs -f api-blue api-green` (look for `"level": "ERROR"`).
If the script prints `did not become ready`, the old release is still serving users. Check `docker compose logs api-<slot>`.

## 2. Rollback
Trigger: error rate > 5%, failing readiness, or a severe bug after a deploy.
1. `./scripts/rollback.sh` (switches traffic back to the previous slot; no rebuild).
2. Confirm `curl localhost:8000/health` shows the old version.
3. Record what failed, which tag, and the evidence (logs).
Further back: `git checkout <old-tag> && ./scripts/deploy.sh <old-tag>`.
Data: no destructive migrations, so the `pgdata` volume is never touched by a rollback.

## 3. Incident response
| Step | Action |
|---|---|
| Detect | Alert (`ApexApiDown`, `ApexDatabaseDown`, `ApexHighErrorRate`) or user report |
| Triage | `/health` OK? `/readiness` OK? Was there a deploy in the last hour? |
| Mitigate | Recent deploy → roll back. DB down → start DB. Otherwise restart the active slot |
| Communicate | Post status and ETA to the team channel every 15 minutes |
| Review | Short postmortem: timeline, root cause, fix, prevention |

Severity: SEV1 = API down; SEV2 = degraded or >5% errors; SEV3 = minor.

### Worked example — database outage
Run `make demo-failure` (illustrative result in `FAILURE_INVESTIGATION.md`). Liveness stays 200 while readiness returns 503 and `apex_db_up` is 0, which is why they are separate endpoints.

## 4. Troubleshooting
| Symptom | Check | Fix |
|---|---|---|
| First deploy hangs on db | `docker compose logs db` | stale volume with a different password → `docker compose down -v` (deletes data) |
| `/readiness` 503 | `docker compose ps`, `logs api-*` | start db; check `.env` credentials |
| Port 8000 in use | `lsof -i :8000` | stop the other process |
| nginx 502 | `docker compose logs nginx`, `ps` | the active slot is down → run `rollback.sh` or redeploy |
| Slot restarting | `docker compose logs api-<slot>` | fix config; roll back |
| Rollback: image not found | `docker images apex-ops-api` | redeploy the older tag with `deploy.sh` |
| Reset everything | — | `make down`, `rm -rf .release`, restore `nginx/default.conf` from git |

## 5. Backups (local scope)
`docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql`
