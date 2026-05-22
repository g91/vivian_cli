#!/usr/bin/env bash
# =============================================================================
# UESDKGen — Cross-platform environment setup  (Linux / macOS / WSL)
# =============================================================================
# Usage:
#   chmod +x setup_env.sh
#   ./setup_env.sh            # create .venv, install deps
#   ./setup_env.sh --clean    # remove .venv, then reinstall
#   ./setup_env.sh --help     # show this help
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MIN_MINOR=10
PREFERRED=("python3.12" "python3.11" "python3.10")

# ── Colors ───────────────────────────────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' C='\033[0;36m' B='\033[1m' N='\033[0m'

info()    { echo -e "${G}[+]${N} $*"; }
warn()    { echo -e "${Y}[!]${N} $*"; }
error()   { echo -e "${R}[✗]${N} $*" >&2; }
header()  { echo -e "\n${C}${B}── $* ──${N}"; }

# ── CLI args ─────────────────────────────────────────────────────────────────
CLEAN=0
for arg in "$@"; do
  case "$arg" in
    --clean)  CLEAN=1 ;;
    --help|-h)
      echo "Usage: $0 [--clean] [--help]"
      echo "  --clean   Remove existing .venv and rebuild from scratch"
      exit 0 ;;
  esac
done

# ── Detect OS ────────────────────────────────────────────────────────────────
OS="unknown"
case "$(uname -s)" in
  Linux*)   OS="linux" ;;
  Darwin*)  OS="macos" ;;
  CYGWIN*|MINGW*|MSYS*) OS="windows_wsl" ;;
esac

# ── 1. Find a suitable Python ─────────────────────────────────────────────────
header "Checking Python"

find_python() {
  # Try preferred versions first, then fall back
  for cmd in "${PREFERRED[@]}" python3 python; do
    if command -v "$cmd" &>/dev/null 2>&1; then
      major=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
      minor=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
      if [ "$major" = "3" ] && [ "$minor" -ge "$MIN_MINOR" ] 2>/dev/null; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON=$(find_python) || {
  error "Python 3.10+ not found on PATH."
  echo ""
  echo "Install instructions:"
  if [ "$OS" = "linux" ]; then
    # Detect distro
    if command -v apt-get &>/dev/null; then
      echo "  Debian/Ubuntu:"
      echo "    sudo add-apt-repository ppa:deadsnakes/ppa  # Ubuntu"
      echo "    sudo apt-get update"
      echo "    sudo apt-get install python3.12 python3.12-venv python3.12-tk"
    elif command -v dnf &>/dev/null; then
      echo "  Fedora/RHEL:"
      echo "    sudo dnf install python3.12 python3-tkinter"
    elif command -v pacman &>/dev/null; then
      echo "  Arch/Manjaro:"
      echo "    sudo pacman -S python tk"
    else
      echo "  Linux (generic):"
      echo "    curl https://pyenv.run | bash"
      echo "    pyenv install 3.12.9 && pyenv global 3.12.9"
    fi
  elif [ "$OS" = "macos" ]; then
    echo "  macOS (Homebrew):"
    echo "    brew install python@3.12 python-tk@3.12"
    echo "  macOS (python.org):"
    echo "    https://www.python.org/downloads/release/python-3129/"
  fi
  echo ""
  echo "  Any platform (pyenv):"
  echo "    curl https://pyenv.run | bash"
  echo "    pyenv install 3.12.9 && pyenv local 3.12.9"
  exit 1
}

PY_VER=$("$PYTHON" --version 2>&1)
info "Found: $PYTHON  ($PY_VER)"

# ── 2. Check tkinter ─────────────────────────────────────────────────────────
header "Checking tkinter"

if "$PYTHON" -c "import tkinter" &>/dev/null 2>&1; then
  info "tkinter OK"
else
  warn "tkinter is NOT available for $PYTHON"
  echo ""
  if [ "$OS" = "linux" ]; then
    if command -v apt-get &>/dev/null; then
      # Try to determine exact pkg name
      PY_SHORT=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      echo "  Install: sudo apt-get install python${PY_SHORT}-tk"
      echo "     or:   sudo apt-get install python3-tk"
    elif command -v dnf &>/dev/null; then
      echo "  Install: sudo dnf install python3-tkinter"
    elif command -v pacman &>/dev/null; then
      echo "  Install: sudo pacman -S tk"
    fi
  elif [ "$OS" = "macos" ]; then
    PY_SHORT=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "  Install: brew install python-tk@${PY_SHORT}"
    echo "     or:   reinstall Python from https://python.org"
  fi
  echo ""
  read -r -p "  Continue without tkinter? The GUI will not work. [y/N] " ans
  case "$ans" in [yY]*) warn "Continuing without tkinter." ;; *)  error "Aborted."; exit 1 ;; esac
fi

# ── 3. Create / clean venv ───────────────────────────────────────────────────
header "Virtual environment"

if [ "$CLEAN" = "1" ] && [ -d "$VENV_DIR" ]; then
  warn "Removing existing venv: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
  info "Creating venv: $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
else
  info "Venv already exists: $VENV_DIR"
fi

# ── 4. Install requirements ───────────────────────────────────────────────────
header "Installing dependencies"

PIP="$VENV_DIR/bin/pip"
"$PIP" install --upgrade pip --quiet
info "pip upgraded"

if [ -f "$REQ_FILE" ]; then
  "$PIP" install -r "$REQ_FILE" --quiet
  info "requirements.txt installed"
else
  warn "requirements.txt not found — skipping"
fi

# ── 5. Verify import ─────────────────────────────────────────────────────────
header "Smoke-testing import"
"$VENV_DIR/bin/python" -c "
import tkinter, pathlib, json, datetime, threading, struct, ctypes
print('[+] Core imports OK')
try:
    import memprocfs
    print('[+] memprocfs OK')
except ImportError:
    print('[!] memprocfs not available (optional — DMA backend only)')
"

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${C}${B}╔══════════════════════════════════════════════════════╗"
echo    "║           UESDKGen environment ready!               ║"
echo    "╠══════════════════════════════════════════════════════╣"
echo    "║  Activate:  source .venv/bin/activate               ║"
echo    "║  Run:       python UESDKGen.py                      ║"
echo    "║  Or:        bash launch.sh                          ║"
echo -e "╚══════════════════════════════════════════════════════╝${N}"
echo ""
