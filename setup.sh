#!/usr/bin/env bash
# Prepara o ambiente de desenvolvimento do fxpricer (Linux e macOS).
#
#   ./setup.sh               instala tudo e roda os testes
#   ./setup.sh --cpp         também compila o núcleo C++
#   ./setup.sh --skip-tests  não roda o pytest no final
set -euo pipefail
cd "$(dirname "$0")"

CPP=0
SKIP_TESTS=0
for arg in "$@"; do
  case "$arg" in
    --cpp) CPP=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "Opção desconhecida: $arg" >&2; exit 1 ;;
  esac
done

step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '    \033[32m%s\033[0m\n' "$1"; }
warn() { printf '    \033[33m%s\033[0m\n' "$1"; }

# ---- 1. Python ---------------------------------------------------------------
step "Procurando Python >= 3.10"
PYTHON=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 &&
     "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PYTHON="$c"; break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3.10+ não encontrado." >&2
  echo "  Ubuntu/Debian: sudo apt install python3 python3-venv" >&2
  echo "  macOS:         brew install python" >&2
  exit 1
fi
ok "Usando: $PYTHON ($("$PYTHON" --version))"

# ---- 2. Ambiente virtual -----------------------------------------------------
step "Ambiente virtual (.venv)"
if [ -x .venv/bin/python ]; then
  ok ".venv já existe, reaproveitando"
else
  "$PYTHON" -m venv .venv || {
    echo "Falha ao criar o .venv. No Ubuntu/Debian: sudo apt install python3-venv" >&2; exit 1; }
  ok ".venv criado"
fi
VENV_PY=".venv/bin/python"

# ---- 3. Dependências ---------------------------------------------------------
step "Instalando dependências"
"$VENV_PY" -m pip install --upgrade pip --quiet
EXTRAS=".[dev]"; [ "$CPP" = 1 ] && EXTRAS=".[dev,cpp]"
"$VENV_PY" -m pip install -e "$EXTRAS" --quiet
ok "Pacote fxpricer instalado em modo editável ($EXTRAS)"

# ---- 4. Kernel do Jupyter ----------------------------------------------------
step "Registrando kernel do Jupyter"
"$VENV_PY" -m ipykernel install --user --name fxpricer --display-name "Python (fxpricer)" >/dev/null
ok "Kernel 'Python (fxpricer)' disponível no Jupyter e no VS Code"

# ---- 5. Configuração ---------------------------------------------------------
step "Arquivo de configuração"
if [ -f config.yaml ]; then
  ok "config.yaml já existe, mantido"
else
  cp config.example.yaml config.yaml
  ok "config.yaml criado a partir de config.example.yaml"
fi

# ---- 6. Núcleo C++ (opcional) ------------------------------------------------
if [ "$CPP" = 1 ]; then
  step "Compilando o núcleo C++"
  if ! command -v c++ >/dev/null 2>&1; then
    warn "Compilador C++ não encontrado. Pulando a compilação."
    warn "  Ubuntu/Debian: sudo apt install build-essential"
    warn "  macOS:         xcode-select --install"
    warn "Depois rode ./setup.sh --cpp de novo. O pacote funciona sem o C++."
  elif .venv/bin/cmake -S cpp -B build -G Ninja -DCMAKE_MAKE_PROGRAM="$PWD/.venv/bin/ninja" \
         -DPython_EXECUTABLE="$PWD/$VENV_PY" &&
       .venv/bin/cmake --build build &&
       .venv/bin/ctest --test-dir build --output-on-failure; then
    ok "Módulo _fxcore compilado em src/fxpricer/"
  else
    warn "A compilação do C++ falhou. O pacote continua funcionando só com Python."
  fi
fi

# ---- 7. Testes ---------------------------------------------------------------
if [ "$SKIP_TESTS" = 0 ]; then
  step "Rodando os testes"
  "$VENV_PY" -m pytest -q
fi

CPP_STATUS=$("$VENV_PY" -c "import fxpricer; print('sim' if fxpricer.CPP_DISPONIVEL else 'não')")
printf '\n\033[32mTudo pronto!\033[0m\n'
echo "  Núcleo C++ disponível: $CPP_STATUS"
echo "  Ative o ambiente:      source .venv/bin/activate"
echo "  Abra o notebook:       jupyter notebook notebooks/01_precificacao.ipynb"
