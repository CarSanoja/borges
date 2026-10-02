BORGES = uv run --no-sync borges
FRONTEND = pnpm -C frontend

.PHONY: install lint test demo-cli demo-red-cards serve dev record-demos live-smoke record-live docker docker-run

install:
	uv sync --extra contree
	$(FRONTEND) install

lint:
	uv run --no-sync ruff check src tests cases scripts
	uv run --no-sync ruff format --check src tests cases scripts

test: lint
	uv run --no-sync pytest -q
	$(FRONTEND) typecheck
	$(FRONTEND) test --run
	$(FRONTEND) build

demo-cli:
	$(BORGES) run --case checkout_ab --llm scripted

demo-red-cards:
	$(BORGES) run --case red_cards --llm scripted

serve: export BORGES_REGISTRY_ENFORCE=true
serve: export BORGES_STORE_KEY_AUTOGEN=true
serve:
	$(FRONTEND) build
	$(BORGES) serve

dev: export BORGES_ALLOW_UNTRUSTED_LOCAL=true
dev:
	$(BORGES) serve --reload & pid=$$!; \
	trap 'kill $$pid' EXIT INT TERM; \
	$(FRONTEND) dev

record-demos:
	$(BORGES) record-demo --case checkout_ab --llm scripted
	$(BORGES) record-demo --case red_cards --llm scripted
	$(BORGES) record-demo --case marp_religiosity --llm scripted
	$(BORGES) record-demo --case marp_norms --llm scripted
	uv run --no-sync python scripts/export_recorded_run.py

live-smoke:
	uv run --no-sync python scripts/live_smoke.py

record-live: export BORGES_RUN_CAP_USD ?= 0.50
record-live: live-smoke
	$(BORGES) record-demo --case checkout_ab --llm nebius
	$(BORGES) record-demo --case red_cards --llm nebius
	$(BORGES) record-demo --case marp_religiosity --llm nebius
	$(BORGES) record-demo --case marp_norms --llm nebius
	$(BORGES) record-demo --case bank_marketing_calls --llm nebius

docker:
	docker build -t borges .

docker-run:
	docker run --rm -p 8000:8000 $(if $(wildcard .env),--env-file .env) borges
