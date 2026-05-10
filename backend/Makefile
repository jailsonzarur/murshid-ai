.PHONY: help install dev start worker test coverage lint typecheck format check clean docker-up docker-down up down generate history current

PORT ?= 8002
n ?= auto

help:
	@echo ""
	@echo "  Ambiente"
	@echo "    make install        Instala dependencias com uv"
	@echo "    make clean          Remove caches locais"
	@echo ""
	@echo "  Servidor"
	@echo "    make dev            Inicia servidor com hot reload na porta $(PORT)"
	@echo "    make start          Inicia servidor na porta $(PORT)"
	@echo "    make worker         Inicia worker Celery"
	@echo ""
	@echo "  Banco"
	@echo "    make docker-up      Sobe Postgres"
	@echo "    make docker-down    Para containers"
	@echo "    make up             Aplica migracoes"
	@echo "    make down           Reverte ultima migracao"
	@echo "    make generate msg=\"descricao\"  Gera migracao"
	@echo ""
	@echo "  Qualidade"
	@echo "    make test           Roda testes"
	@echo "    make coverage       Roda testes com cobertura"
	@echo "    make lint           Roda ruff"
	@echo "    make typecheck      Roda basedpyright"
	@echo "    make check          Roda lint e testes"
	@echo ""

install:
	uv sync

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port $(PORT)

start:
	uv run uvicorn src.main:app --host 0.0.0.0 --port $(PORT)

worker:
	uv run celery -A src.core.celery.celery_app worker --loglevel=info

docker-up:
	docker compose up -d

docker-down:
	docker compose down

generate:
	uv run alembic revision --autogenerate -m "$(msg)"

up:
	uv run alembic upgrade head

down:
	uv run alembic downgrade -1

history:
	uv run alembic history

current:
	uv run alembic current

test:
	uv run pytest src/tests -n $(n)

coverage:
	uv run pytest src/tests -n $(n) --cov=src --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check src

format:
	uv run ruff format src

typecheck:
	uv run basedpyright src

check: lint test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .cache .coverage htmlcov src/tests/.coverage src/tests/htmlcov
