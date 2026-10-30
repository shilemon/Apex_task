.PHONY: setup test lint up down logs deploy rollback demo-failure scan pin-base

pin-base:
	./scripts/pin_base_image.sh

V ?= v1.0.0

setup:
	@test -f .env || cp .env.example .env
	pip install -r requirements-dev.txt

lint:
	ruff check .

test:
	pytest -v

# First deployment (blue slot + db + nginx)
up:
	@test -f .env || cp .env.example .env
	./scripts/deploy.sh $(V)

down:
	docker compose --profile green --profile monitoring down
	rm -rf .release

logs:
	docker compose logs -f api-blue api-green

deploy:
	./scripts/deploy.sh $(V)

rollback:
	./scripts/rollback.sh

demo-failure:
	./scripts/failure_demo.sh

# Local image scan (requires trivy installed): make scan V=v1.0.0
scan:
	trivy image --severity HIGH,CRITICAL --ignore-unfixed apex-ops-api:$(V)
