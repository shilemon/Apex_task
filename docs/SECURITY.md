# Security notes

## Secrets handling
- No secrets in the repo. `.env` is git-ignored; `.env.example` has placeholders only.
- App reads `DATABASE_URL` from the environment; Compose builds it from `.env`.
- CI generates a throwaway random password per run; registry login uses the built-in `GITHUB_TOKEN` (scoped, short-lived).
- Cloud path: AWS Secrets Manager injected at runtime, GitHub→AWS via OIDC (no stored access keys), rotate regularly. See `AWS_PATH.md`.
- If a secret is ever committed: rotate it first, then remove it from history.

## Least privilege
- Container runs as non-root UID 10001, no shell login, no home directory.
- `cap_drop: ALL`, `no-new-privileges`, read-only root filesystem (+ tmpfs `/tmp`).
- Only nginx publishes a host port; the API and the database are on an internal Compose network.
- CI workflow default permission is `contents: read`; only the `publish` job gets `packages: write`.
- Improvement: use a dedicated DB role limited to table privileges instead of the owner role.

## Vulnerability scanning
- Dependencies: `pip-audit -r requirements.txt` in CI (fails the build on known CVEs).
- Image: Trivy in CI (fails on CRITICAL, ignores unfixed). Local: `make scan V=v1.0.0` or
  `trivy image --severity HIGH,CRITICAL --ignore-unfixed apex-ops-api:v1.0.0`.
- Postgres and nginx images use exact version tags (`postgres:16.6-alpine`, `nginx:1.27.3-alpine`); the Python base is a maintained minor-line tag that `scripts/pin_base_image.sh` pins by digest. Multi-stage build keeps the runtime small.

## Scan results and remediation (real run)
First Trivy scan of `apex-ops-api:v1.0.0` (built on `python:3.12.8-slim-bookworm`, Debian 12.9):
- OS packages: 54 HIGH/CRITICAL findings (7 CRITICAL) in openssl, gnutls, perl-base, krb5, pcre2 and others; fixed versions existed in Debian security updates.
- Python packages: 3 HIGH findings in `starlette 0.41.3` (fixed in 1.x).
- Evidence: `evidence/trivy_scan_before.txt`.

Remediation:
1. Dockerfile now uses the maintained `python:3.12-slim-bookworm` line and runs `apt-get upgrade` in the runtime stage to take Debian security fixes.
2. Runtime dependencies bumped (`fastapi 0.162.0`, `starlette 1.10.0`, ...); `pip-audit` reports no known vulnerabilities for the pinned set; tests re-run and pass.
3. Rebuild and rescan; save the result as `evidence/trivy_scan_after.txt`. Any remaining finding with no available fix is listed here with a risk note.
4. `./scripts/pin_base_image.sh` pins the base image by digest once the scan is clean (trade-off: a pinned digest needs a deliberate refresh to receive new fixes; CI scanning catches the drift).

## Known gaps (honest list)
No API authentication, no TLS (would terminate at nginx/ALB), no rate limiting, no image signing (cosign), schema created at startup rather than with migrations, base image digests not pinned.
