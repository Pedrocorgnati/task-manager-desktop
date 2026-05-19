# Makefile gerado por /dev-bootstrap-create (SystemForge)
# Task Manager Desktop — PySide6 + Python

.PHONY: setup reset dev test lint typecheck help

# === Setup & Reset ===
setup:
	@./scripts/bootstrap.sh

reset:
	@./scripts/bootstrap.sh --reset

health:
	@./scripts/bootstrap.sh --health

# === Development ===
dev:
	@python -m task_manager_desktop

# === Testing ===
test:
	@pytest tests/ tests-tdd/ -v

test-unit:
	@pytest tests/ -v

test-tdd:
	@pytest tests-tdd/ -v

test-cov:
	@pytest tests/ tests-tdd/ --cov=task_manager_desktop --cov-report=html --cov-report=term-missing

# === Code Quality ===
lint:
	@ruff check .

typecheck:
	@mypy task_manager_desktop --ignore-missing-imports

check: lint typecheck
	@echo "✓ Linting and typecheck passed"

# === Utilities ===
clean:
	@rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned"

venv:
	@python3 -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

install:
	@pip install -e .

install-dev:
	@pip install -e .[dev]

audit:
	@pip-audit || echo "pip-audit nao instalado: pip install pip-audit"

help:
	@echo "Task Manager Desktop — Available targets:"
	@echo ""
	@echo "  setup              Setup ambiente (install deps, create venv, run checks)"
	@echo "  reset              Reset completo (remove venv, .env, caches)"
	@echo "  health             Health check rapido"
	@echo ""
	@echo "  dev                Executar aplicacao (python -m task_manager_desktop)"
	@echo ""
	@echo "  test               Rodar todos os testes (unit + TDD)"
	@echo "  test-unit          Apenas testes unitarios"
	@echo "  test-tdd           Apenas testes TDD"
	@echo "  test-cov           Testes com coverage report"
	@echo ""
	@echo "  lint               Ruff check (linting)"
	@echo "  typecheck          Mypy typecheck"
	@echo "  check              Lint + typecheck"
	@echo ""
	@echo "  clean              Remover .venv, caches, .pyc"
	@echo "  venv               Criar novo virtualenv"
	@echo "  install            Instalar dependencias de runtime"
	@echo "  install-dev        Instalar dependencias de dev"
	@echo ""
	@echo "  help               Esta mensagem"
