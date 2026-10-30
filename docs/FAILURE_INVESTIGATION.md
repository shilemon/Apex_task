# Failure investigation: database outage (real run, 2026-10-30)

Raw log: `evidence/failure_demo.log` (produced by `make demo-failure`).

## Timeline
- 17:19:30 Baseline: `/readiness` -> 200 `{"status":"ready","database":"up"}`
- 17:19:30 Injected failure: `docker compose stop db`
- 17:19:33 Symptoms: `/health` -> 200, `/readiness` -> 503 `{"status":"not_ready","database":"down"}`
- 17:19:33 Investigated, then recovered by starting the db
- 17:19:36 Verified: `/readiness` -> 200

## Investigation
1. Compared liveness and readiness: the process is alive (200) but not ready (503), so the fault is a dependency, not the app.
2. API logs: structured JSON with `level=ERROR msg=db_unavailable` and a name resolution error for host `db`.
3. Metrics: `apex_db_up 0.0`.
4. Container state: `docker compose ps` lists no `db` container (use `ps -a` to see it exited).

## Root cause
The Postgres container was stopped, so the `db` hostname no longer resolved.

## Fix and verification
`docker compose start db`. Readiness returned 200 within seconds with no API restart, because readiness re-checks the database on every probe.

## Prevention
- Alert on `apex_db_up == 0` for 1 minute (see docs/MONITORING.md).
- Readiness removes an unhealthy slot from rotation in a real load balancer.
- Next step in production: managed database with automated failover.