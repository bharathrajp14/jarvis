#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "========================================================"
echo "  BR-JARVIS reproducible Linux environment setup"
echo "========================================================"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] python3 is required." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if not ((3, 11) <= sys.version_info[:2] <= (3, 13)):
    raise SystemExit("[ERROR] Python 3.11-3.13 is required")
PY

if [[ ! -x .venv/bin/python ]]; then
  echo "[INFO] Creating .venv..."
  "$PYTHON_BIN" -m venv .venv
fi

VENV_PY=".venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

INSTALL_TARGET='.[documents,web,llm-backends]'
if [[ "${1:-}" == "--dev" ]]; then
  INSTALL_TARGET='.[documents,web,llm-backends,dev]'
fi

echo "[INFO] Installing ${INSTALL_TARGET} from pyproject.toml..."
"$VENV_PY" -m pip install -e "$INSTALL_TARGET"
"$VENV_PY" -m pip check

if [[ ! -f .env ]]; then
  cp .env.template .env
  chmod 600 .env || true
  echo "[ACTION REQUIRED] .env was created. Replace the JARVIS_SERVER_API_KEY placeholder."
fi

if [[ -f scripts/setup_native.py ]]; then
  "$VENV_PY" scripts/setup_native.py || echo "[WARN] Optional native extension unavailable; Python fallback remains active."
fi

echo "[OK] Environment ready."
echo "     Optional voice/desktop bundle: .venv/bin/python -m pip install -e '.[voice,automation]'"
echo "     Run: .venv/bin/python start.py status"
echo "     Web: .venv/bin/python start.py web"
