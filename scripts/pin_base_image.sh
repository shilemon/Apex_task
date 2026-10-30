#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")/.."

IMG="${1:-python:3.12-slim-bookworm}"
docker pull "$IMG" >/dev/null
REPO_DIGEST="$(docker inspect --format '{{index .RepoDigests 0}}' "$IMG")"   # python@sha256:...
DIGEST="${REPO_DIGEST#*@}"
sed -i "s|^ARG PYTHON_IMAGE=.*|ARG PYTHON_IMAGE=${IMG}@${DIGEST}|" Dockerfile
echo "Pinned base image: ${IMG}@${DIGEST}"
grep -n '^ARG PYTHON_IMAGE' Dockerfile
