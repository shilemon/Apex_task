# Release strategy — versioning, zero-downtime deploys, rollback

## Semantic versioning (`MAJOR.MINOR.PATCH`)
| Bump | When | Example |
|---|---|---|
| PATCH | bug fix, no API change | `v1.0.0` → `v1.0.1` |
| MINOR | new backward-compatible endpoint/field | `v1.0.1` → `v1.1.0` |
| MAJOR | breaking API or schema change | `v1.4.2` → `v2.0.0` |

Release steps:
1. Merge to `main` only when CI is green.
2. Tag: `git tag -a v1.1.0 -m "Add PUT/DELETE incidents" && git push origin v1.1.0`.
3. CI publishes `ghcr.io/<owner>/<repo>:1.1.0`, `:1.1` and `:<full-sha>`. There is no `latest` tag on purpose: every running image is traceable to one commit.
4. Deploy locally with `./scripts/deploy.sh v1.1.0` (the same tag name the container reports at `/health`).

## Zero-downtime-style deployment (blue/green behind nginx)
```
client → nginx:8000 → api-blue  (active, v1.0.0)
                      api-green (idle,   v1.1.0 being started)
```
1. Build `apex-ops-api:<new-tag>` and start it in the idle slot.
2. Compose waits for the slot's healthcheck on `/readiness` (database reachable).
3. nginx config is switched and reloaded gracefully (`nginx -s reload`): existing connections finish on the old slot.
4. Old slot is stopped after a short drain; its image remains for rollback.
If step 1 or 2 fails, nothing changes for users. If the post-switch check fails, the script reverts nginx to the old slot.

Honest limits: single host (nginx and Postgres are single instances); database migrations must be backward compatible (expand → deploy → contract) because old and new versions briefly overlap.

## Rollback
`./scripts/rollback.sh` brings the previous slot back (no rebuild), switches nginx, stops the bad slot. It takes seconds because the old image and the slot definition still exist. To go further back, redeploy an older tag: `git checkout v1.0.0 && ./scripts/deploy.sh v1.0.0`.
State lives in `.release/state.env` (active slot and the tag in each slot).
