BORGES = uv run --no-sync borges
FRONTEND = pnpm -C frontend

.PHONY: install lint test demo-cli demo-red-cards serve dev record-demos docker docker-run

install:
	uv sync --extra contree
	$(FRONTEND) install

lint:
	uv run --no-sync ruff check src tests cases
	uv run --no-sync ruff format --check src tests cases

test: lint
	uv run --no-sync pytest -q
	$(FRONTEND) typecheck
	$(FRONTEND) test --run
	$(FRONTEND) build

demo-cli:
	$(BORGES) run --case checkout_ab --llm scripted

demo-red-cards:
	$(BORGES) run --case red_cards --llm scripted

serve:
	$(FRONTEND) build
	$(BORGES) serve

dev:
	$(BORGES) serve --reload & pid=$$!; \
	trap 'kill $$pid' EXIT INT TERM; \
	$(FRONTEND) dev

record-demos:
	$(BORGES) record-demo --case checkout_ab --llm scripted
	$(BORGES) record-demo --case red_cards --llm scripted

docker:
	docker build -t borges .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env borges
