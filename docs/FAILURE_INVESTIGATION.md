# Failure investigation log — SIMULATED EXAMPLE

> This is an illustrative walkthrough of what `make demo-failure` is expected to show. **Replace it with your real output from `evidence/failure_demo.log` after you run the demo.** Do not submit this text as proof of execution.

**Scenario:** the database container stops while the API keeps running.

| # | Action | Observation | Conclusion |
|---|---|---|---|
| 1 | Baseline: `curl /readiness` | `{"status":"ready","database":"up"} http=200` | healthy |
| 2 | Inject: `docker compose stop db` | — | — |
| 3 | `curl /health` | `{"status":"ok"} http=200` | process alive (liveness unaffected) |
| 4 | `curl /readiness` | `{"status":"not_ready","database":"down"} http=503` | API cannot serve traffic |
| 5 | `docker compose logs api-blue` | `{"level":"ERROR","msg":"db_unavailable",...}` | error originates from DB connection |
| 6 | `curl /metrics \| grep apex_db_up` | `apex_db_up 0.0` | matches `ApexDatabaseDown` alert |
| 7 | `docker compose ps` | `db` shows `exited` | root cause: db container stopped |
| 8 | Fix: `docker compose start db` | db becomes healthy | — |
| 9 | `curl /readiness` | `http=200`; data still present (named volume) | recovered |

**Root cause:** database container stopped. **Detection:** readiness 503, `apex_db_up 0`, ERROR logs. **Prevention ideas:** `restart: unless-stopped` (already set), alert on `apex_db_up`, managed database with automated failover in cloud.
