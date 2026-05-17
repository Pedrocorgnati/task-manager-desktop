#!/usr/bin/env bash
# bootstrap.sh — Setup completo do ambiente local
# Gerado por /dev-bootstrap-create (SystemForge)
# Uso: ./scripts/bootstrap.sh [--reset | --health]
set -euo pipefail

# === Cores ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[bootstrap]${NC} $*"; }
ok()   { echo -e "${GREEN}[ok]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[erro]${NC} $*" >&2; }

# === Pre-requisitos ===
check_prereqs() {
  local missing=()

  command -v git >/dev/null 2>&1 || missing+=("git")
  command -v python3 >/dev/null 2>&1 || missing+=("python3")
  command -v pip >/dev/null 2>&1 || missing+=("pip")

  if [ ${#missing[@]} -gt 0 ]; then
    err "Faltando: ${missing[*]}"
    err "Instale os pre-requisitos acima e tente novamente."
    exit 1
  fi
  ok "Pre-requisitos verificados (git, python3, pip)"
}

# === .env ===
ensure_env() {
  if [ -f .env ]; then
    ok ".env ja existe"
    return
  fi

  if [ -f .env.example ]; then
    cp .env.example .env
    ok ".env criado a partir de .env.example"
    warn "Revise .env e preencha valores sensiveis antes de continuar"
  else
    warn ".env nao encontrado e sem template. Crie manualmente ou execute /env-creation"
  fi
}

# === Virtualenv ===
ensure_venv() {
  if [ -d .venv ]; then
    ok "Virtualenv ja existe"
  else
    log "Criando virtualenv..."
    python3 -m venv .venv
    ok "Virtualenv criado"
  fi

  # Ativar
  # shellcheck disable=SC1091
  source .venv/bin/activate
  ok "Virtualenv ativado"
}

# === Dependencias ===
install_deps() {
  log "Instalando dependencias de runtime..."
  pip install -r requirements.txt
  ok "Dependencias de runtime instaladas"

  log "Instalando dependencias de desenvolvimento..."
  pip install -r requirements-dev.txt
  ok "Dependencias de desenvolvimento instaladas"
}

# === Typecheck e Lint ===
run_checks() {
  log "Executando ruff check..."
  ruff check . || warn "Ruff encontrou problemas (nao-bloqueante)"

  log "Executando mypy..."
  mypy task_manager_desktop --ignore-missing-imports || warn "Mypy encontrou problemas (nao-bloqueante)"

  ok "Typecheck e lint concluidos"
}

# === Testes ===
run_tests() {
  log "Executando testes unitarios..."
  pytest tests/ -v --tb=short
  ok "Testes unitarios concluidos"

  log "Executando testes TDD..."
  pytest tests-tdd/ -v --tb=short || warn "Alguns testes TDD podem estar em RED (esperado em ciclos iniciais)"

  ok "Ciclo de testes concluido"
}

# === Health Check (leve) ===
check_health() {
  log "Verificando saude do ambiente..."
  local errors=0

  # Verificar .env
  if [ -f .env ]; then
    ok ".env presente"
  else
    warn ".env ausente"
    errors=$((errors + 1))
  fi

  # Verificar virtualenv
  if [ -d .venv ]; then
    ok "Virtualenv presente"
  else
    warn "Virtualenv ausente"
    errors=$((errors + 1))
  fi

  # Verificar importacoes basicas
  log "Verificando importacoes..."
  if python3 -c "from task_manager_desktop import __version__; print(f'App v{__version__}')" 2>/dev/null; then
    ok "Modulo principal importavel"
  else
    warn "Modulo principal nao importavel"
    errors=$((errors + 1))
  fi

  if [ $errors -eq 0 ]; then
    ok "Ambiente saudavel"
  else
    warn "$errors problema(s) encontrado(s) — verifique acima"
  fi
}

# === Resumo ===
show_summary() {
  echo ""
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  BOOTSTRAP COMPLETO${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "  Para ativar o virtualenv:"
  echo "    source .venv/bin/activate"
  echo ""
  echo "  Para iniciar a aplicacao:"
  echo "    python -m task_manager_desktop   (ou: make dev)"
  echo ""
  echo "  Para rodar testes:"
  echo "    pytest   (ou: make test)"
  echo ""
  echo "  Para resetar tudo:"
  echo "    ./scripts/bootstrap.sh --reset"
  echo ""
}

# === Reset ===
do_reset() {
  warn "Resetando ambiente..."
  rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache 2>/dev/null || true
  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find . -type f -name "*.pyc" -delete 2>/dev/null || true
  rm -f .env 2>/dev/null || true
  ok "Ambiente limpo"
  do_setup
}

# === Setup principal ===
do_setup() {
  log "Iniciando bootstrap de task-manager-desktop..."
  echo ""

  check_prereqs
  ensure_env
  ensure_venv
  install_deps
  run_checks
  check_health
  show_summary
}

# === Entrypoint ===
cd "$(dirname "$0")/.."

case "${1:-}" in
  --reset) do_reset ;;
  --health) check_health ;;
  --tests) run_tests ;;
  *) do_setup ;;
esac
