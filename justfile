serve:
	uv run bin/helios serve

migrate:
	uv run bin/helios migrate

migrate-status:
	uv run bin/helios migrate:status

test:
	uv run bin/helios assets:compile
	uv run luna test

lint:
	uv run ruff format
	uv run ruff check --fix

check:
	uv run ty check
