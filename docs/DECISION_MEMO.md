# Decision memo

| Decision | Why | Trade-off |
|---|---|---|
| FastAPI + SQLAlchemy | Small, readable, easy to explain; built-in validation | Less "enterprise" than Java/.NET |
| PostgreSQL in Compose | Realistic dependency with a persistent volume | Heavier than SQLite; unit tests use SQLite for speed |
| Separate `/health` and `/readiness` | Liveness must not fail because the DB is down; readiness should | Two endpoints to maintain |
| Image tag = semantic version | Immutable, rollback is switching to a tagged image | Tags must be kept locally/in a registry |
| nginx blue/green slots | Switch traffic only after the new version is ready; graceful reload | More moving parts; single-host only |
| Rollback = switch back to the previous slot | Seconds, no rebuild | Does not revert DB schema (backward-compatible migrations required) |
| JSON logs + Prometheus metrics | Easy to parse; standard alert rules | No log aggregation locally |
| GitHub Actions `needs:` gates | Build, push and deploy cannot run if lint/test/scan fails | Deploy is a local smoke test on the runner, not a real server |
| Push to GHCR with semver + SHA tags | Free registry, traceable images, no `latest` | Needs a tag push to publish a semver tag |
| Intentional-failure test behind an env flag | Demonstrates the gate without leaving CI red | Needs a manual workflow run to show it |

## Cloud cost-aware path
See `AWS_PATH.md`: Compose on one small instance → ECS Fargate + RDS → hardening only when needed.

## What I would improve with more time
Authentication, Alembic migrations, digest-pinned base images and image signing, Grafana dashboards shipped as code, Alertmanager routing, canary releases, integration tests against Postgres in CI.

## Assumptions
Synthetic data only; single host; no paid cloud; reviewers have Docker installed.
