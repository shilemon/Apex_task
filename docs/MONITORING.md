# Monitoring, metrics and alerting proposal

## What is implemented
- Structured JSON logs on stdout (`ts`, `level`, `msg`, `version`, `request_id`, `method`, `path`, `status`, `duration_ms`).
- Prometheus metrics at `/metrics`: `apex_http_requests_total{method,path,status}`, `apex_http_request_seconds` (histogram), `apex_db_up` (gauge).
- Health checks: `/health` (liveness), `/readiness` (database), plus container healthchecks used by the blue/green deploy.
- Prometheus + alert rules (`monitoring/`), started with `docker compose --profile monitoring up -d` → http://localhost:9090.

## Alert proposal (see `monitoring/alerts.yml`)
| Alert | Condition | Severity | First action |
|---|---|---|---|
| ApexApiDown | `up == 0` for 1m | critical | check `docker compose ps`; roll back if a deploy just happened |
| ApexDatabaseDown | `apex_db_up == 0` for 1m | critical | check/start db container |
| ApexHighErrorRate | 5xx ratio > 5% for 5m | warning | check logs; roll back |
| ApexSlowRequests | p95 latency > 500 ms for 10m | warning | check DB load, recent change |

## Grafana dashboard proposal (not shipped; add Prometheus as a data source)
| Panel | PromQL |
|---|---|
| Request rate | `sum(rate(apex_http_requests_total[1m])) by (path)` |
| Error ratio | `sum(rate(apex_http_requests_total{status=~"5.."}[5m])) / sum(rate(apex_http_requests_total[5m]))` |
| p95 latency | `histogram_quantile(0.95, sum(rate(apex_http_request_seconds_bucket[5m])) by (le))` |
| Database up | `apex_db_up` |
| Running version | from logs/`/health` (label on deploy annotations) |

## Cloud path
CloudWatch Logs for container logs, Amazon Managed Prometheus + Managed Grafana (or CloudWatch alarms) for metrics, SNS → email/Slack for alert delivery.
