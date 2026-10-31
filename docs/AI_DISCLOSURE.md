# AI-use disclosure

I used an AI assistant (Claude by Anthropic) in a chat session during this assessment. Specific uses are listed below.

## What the AI did
- Drafted the first version of the FastAPI app, the pytest suite, the multi-stage non-root Dockerfile, docker-compose.yml, the nginx blue/green configuration and the deploy, rollback and failure-demo scripts.
- Drafted the GitHub Actions workflow and the first version of the documentation (README, runbook, release, monitoring, security, AWS path, decision memo).
- Suggested fixes when I pasted errors (Python virtual environment, Docker and Trivy usage, Git authentication).

## What I did myself
- Ran the project on my own machine (Ubuntu with Docker): tests, deployments, rollback, the database failure demo and the Trivy scans.
- Found and reported problems by running it: the stale release state after `make down`, the Trivy findings (54 OS and 3 Python, fixed and rescanned clean), the non-existent Trivy action tag in CI, and the password mismatch caused by changing POSTGRES_PASSWORD after the database volume existed.
- Created the GitHub repository and SSH key, pushed the code, ran the workflow (green run and intentional-failure red run) and tagged v1.0.4.
- Captured the evidence in the evidence folder and reviewed the code so I can explain it in the live review.

## What the AI got wrong (found by running it)
- The first deploy.sh trusted stale saved state and failed on the first run.
- The first image used an outdated base image and dependency versions with known vulnerabilities.
- The first CI workflow used a Trivy action version that does not exist and a pytest step that could hide a failure.

Nothing in this repository is claimed to have been run unless matching evidence exists in the evidence folder.
