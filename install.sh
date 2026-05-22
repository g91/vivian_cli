#!/usr/bin/env bash
# =============================================================================
# Vivian CLI — Cross-Platform Install Script (Linux / macOS / WSL)
# =============================================================================
# Installs Vivian AI CLI as a system-wide `vivian` and `ai` command.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh                  # Install to ~/.vivian_cli (user)
#   ./install.sh --system         # Install to /opt/vivian_cli (system-wide)
#   ./install.sh --dev            # Editable pip install for development
#   ./install.sh --uninstall      # Remove Vivian CLI
#
# What it does:
#   1. Checks Python 3.10+ is available
#   2. Creates a virtual environment
#   3. Installs dependencies (prompt_toolkit)
#   4. Creates `vivian` and `ai` wrapper scripts in PATH
#   5. Sets up ~/.vivian/ config directory
# =============================================================================

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Banner ──────────────────────────────────────────────────────────────────
banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║   ██╗   ██╗██╗██╗   ██╗██╗ █████╗ ███╗   ██╗  ║"
    echo "║   ██║   ██║██║██║   ██║██║██╔══██╗████╗  ██║  ║"
    echo "║   ██║   ██║██║██║   ██║██║███████║██╔██╗ ██║  ║"
    echo "║   ╚██╗ ██╔╝██║██║   ██║██║██╔══██║██║╚██╗██║  ║"
    echo "║    ╚████╔╝ ██║╚██████╔╝██║██║  ██║██║ ╚████║  ║"
    echo "║     ╚═══╝  ╚═╝ ╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝  ║"
    echo "║              AI-Powered CLI Assistant          ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ── Defaults ────────────────────────────────────────────────────────────────
INSTALL_MODE="user"
DEV_MODE=false
UNINSTALL=false
VIVIAN_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --system|-s)
            INSTALL_MODE="system"
            shift
            ;;
        --dev|-d)
            DEV_MODE=true
            shift
            ;;
        --uninstall|-u)
            UNINSTALL=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --system, -s    Install system-wide to /opt/vivian_cli"
            echo "  --dev, -d       Editable pip install (for development)"
            echo "  --uninstall, -u Remove Vivian CLI"
            echo "  --help, -h      Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage."
            exit 1
            ;;
    esac
done

# ── Determine install paths ─────────────────────────────────────────────────
if [ "$INSTALL_MODE" = "system" ]; then
    INSTALL_DIR="/opt/vivian_cli"
    BIN_DIR="/usr/local/bin"
    VENV_DIR="$INSTALL_DIR/venv"
    NEEDS_SUDO=true
else
    INSTALL_DIR="$HOME/.vivian_cli"
    BIN_DIR="$HOME/.local/bin"
    VENV_DIR="$INSTALL_DIR/venv"
    NEEDS_SUDO=false
fi

CONFIG_DIR="$HOME/.vivian"

# ── Sudo helper ─────────────────────────────────────────────────────────────
as_root() {
    if [ "$NEEDS_SUDO" = true ] && [ "$(id -u)" != "0" ]; then
        sudo "$@"
    else
        "$@"
    fi
}

# ── Uninstall ───────────────────────────────────────────────────────────────
do_uninstall() {
    echo -e "${YELLOW}Uninstalling Vivian CLI...${NC}"

    # Remove wrapper scripts
    for cmd in vivian ai; do
        if [ -f "$BIN_DIR/$cmd" ]; then
            echo "  Removing $BIN_DIR/$cmd"
            as_root rm -f "$BIN_DIR/$cmd"
        fi
    done

    # Remove pip-installed package
    if pip show vivian-cli &>/dev/null; then
        echo "  Removing pip package"
        pip uninstall -y vivian-cli 2>/dev/null || true
    fi

    # Remove install directory
    if [ -d "$INSTALL_DIR" ]; then
        echo "  Removing $INSTALL_DIR"
        as_root rm -rf "$INSTALL_DIR"
    fi

    # Ask about config
    if [ -d "$CONFIG_DIR" ]; then
        echo ""
        read -rp "Remove config directory ($CONFIG_DIR)? [y/N] " answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            rm -rf "$CONFIG_DIR"
            echo "  Removed $CONFIG_DIR"
        else
            echo "  Kept $CONFIG_DIR"
        fi
    fi

    echo -e "${GREEN}Vivian CLI uninstalled.${NC}"
    exit 0
}

# ── Run uninstall if requested ──────────────────────────────────────────────
if [ "$UNINSTALL" = true ]; then
    do_uninstall
fi

# ── Main install ────────────────────────────────────────────────────────────
banner

echo -e "${BOLD}Installing Vivian CLI...${NC}"
echo ""
echo -e "  Install mode:  ${BLUE}$INSTALL_MODE${NC}"
echo -e "  Source:        ${BLUE}$VIVIAN_SOURCE_DIR${NC}"
echo -e "  Install dir:   ${BLUE}$INSTALL_DIR${NC}"
echo -e "  Binary dir:    ${BLUE}$BIN_DIR${NC}"
echo ""

# ── Step 1: Check Python ────────────────────────────────────────────────────
echo -e "${BOLD}[1/6]${NC} Checking Python..."

PYTHON=""
PYTHON_VER=""

# Prefer newer patch releases; fall back gracefully
for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        _ver=$("$candidate" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')" 2>/dev/null || true)
        if [ -n "$_ver" ]; then
            _major=$(echo "$_ver" | cut -d. -f1)
            _minor=$(echo "$_ver" | cut -d. -f2)
            if [ "$_major" -ge 3 ] && [ "$_minor" -ge 10 ] 2>/dev/null; then
                PYTHON="$candidate"
                PYTHON_VER="$_ver"
                break
            fi
        fi
    fi
done

# ── Try pyenv if no system Python 3.10+ was found ───────────────────────────
if [ -z "$PYTHON" ]; then
    PYENV_BIN="$(command -v pyenv 2>/dev/null || echo "$HOME/.pyenv/bin/pyenv")"
    if [ -x "$PYENV_BIN" ]; then
        echo -e "  ${YELLOW}⚠${NC}  System Python 3.10+ not found — trying pyenv..."
        "$PYENV_BIN" install 3.12.9 --skip-existing -q 2>/dev/null || true
        _pyenv_python="$("$PYENV_BIN" prefix 3.12.9 2>/dev/null)/bin/python3"
        if [ -x "$_pyenv_python" ]; then
            PYTHON="$_pyenv_python"
            PYTHON_VER=$("$PYTHON" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')" 2>/dev/null)
        fi
    fi
fi

# ── Auto-install via pyenv if still missing ──────────────────────────────────
if [ -z "$PYTHON" ]; then
    echo -e "  ${YELLOW}⚠${NC}  Python 3.10+ not found."
    OS_TYPE="$(uname -s)"
    echo ""
    echo "  Install Python 3.12, then re-run this script."
    if [[ "$OS_TYPE" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            echo "  Debian/Ubuntu:"
            echo "    sudo add-apt-repository ppa:deadsnakes/ppa   # Ubuntu 20.04/22.04"
            echo "    sudo apt-get update"
            echo "    sudo apt-get install -y python3.12 python3.12-venv python3.12-tk"
        elif command -v dnf &>/dev/null; then
            echo "  Fedora/RHEL:"
            echo "    sudo dnf install python3.12 python3.12-tkinter"
        elif command -v pacman &>/dev/null; then
            echo "  Arch/Manjaro:"
            echo "    sudo pacman -S python tk"
        fi
    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        echo "  macOS (Homebrew):"
        echo "    brew install python@3.12 python-tk@3.12"
        echo "  macOS (python.org installer):"
        echo "    https://www.python.org/downloads/release/python-3129/"
    fi
    echo ""
    echo "  Any platform (pyenv):"
    echo "    curl https://pyenv.run | bash"
    echo "    pyenv install 3.12.9 && pyenv global 3.12.9"
    echo "    then re-run:  ./install.sh"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Found: $PYTHON  (Python $PYTHON_VER)"

# ── 1.5: Verify tkinter (needed for GUI apps like UESDKGen) ─────────────────
if "$PYTHON" -c "import tkinter" &>/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} tkinter available"
else
    echo -e "  ${YELLOW}⚠${NC}  tkinter not found for $PYTHON"
    echo "     GUI apps (e.g. UESDKGen) require tkinter."
    PY_SHORT=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    OS_TYPE="$(uname -s)"
    if [[ "$OS_TYPE" == "Linux" ]]; then
        if command -v apt-get &>/dev/null; then
            echo "     Fix:  sudo apt-get install python${PY_SHORT}-tk"
        elif command -v dnf &>/dev/null; then
            echo "     Fix:  sudo dnf install python3-tkinter"
        elif command -v pacman &>/dev/null; then
            echo "     Fix:  sudo pacman -S tk"
        fi
    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        echo "     Fix:  brew install python-tk@${PY_SHORT}"
    fi
    echo "     Continuing — the CLI works fine without tkinter."
fi

# ── Step 2: Create directories ──────────────────────────────────────────────
echo -e "${BOLD}[2/6]${NC} Creating directories..."

as_root mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$BIN_DIR"

echo -e "  ${GREEN}✓${NC} Directories created"

# ── Step 3: Copy source ─────────────────────────────────────────────────────
echo -e "${BOLD}[3/6]${NC} Copying Vivian CLI source..."

if [ "$DEV_MODE" = true ]; then
    echo -e "  ${YELLOW}Dev mode: using source directly from $VIVIAN_SOURCE_DIR${NC}"
    ACTUAL_SOURCE="$VIVIAN_SOURCE_DIR"
else
    # Copy all files except install script, venv, __pycache__, .git
    echo "  Copying files..."
    as_root rsync -a --exclude='install.sh' --exclude='install.ps1' \
        --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='.git' --exclude='.gitignore' \
        "$VIVIAN_SOURCE_DIR/" "$INSTALL_DIR/" 2>/dev/null || \
    as_root cp -r "$VIVIAN_SOURCE_DIR"/* "$INSTALL_DIR/" 2>/dev/null || {
        # Fallback: copy without rsync
        echo "  Using cp fallback..."
        as_root rm -rf "$INSTALL_DIR"/*
        for item in "$VIVIAN_SOURCE_DIR"/*; do
            name=$(basename "$item")
            case "$name" in
                install.sh|install.ps1|venv|__pycache__|.git|.gitignore)
                    continue
                    ;;
                *)
                    as_root cp -r "$item" "$INSTALL_DIR/"
                    ;;
            esac
        done
    }
    ACTUAL_SOURCE="$INSTALL_DIR"
fi

echo -e "  ${GREEN}✓${NC} Source copied to $INSTALL_DIR"

# ── Step 4: Create virtual environment & install deps ───────────────────────
echo -e "${BOLD}[4/6]${NC} Setting up Python environment..."

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
fi

# Activate venv and install
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "  Upgrading pip..."
pip install --upgrade pip -q

# ── Optional extras ───────────────────────────────────────────────────────────
EXTRAS=""
echo ""
echo -e "  ${BOLD}Optional feature packs${NC}  (can be added later: pip install -e \".[extra]\")"
echo ""

read -rp "  Install dev tools? (pytest, black, ruff) [Y/n] " _ans_dev
[[ "$_ans_dev" =~ ^[Nn] ]] || EXTRAS="${EXTRAS},dev"

read -rp "  Install screen-capture/vision tools? (opencv, Pillow, mss) [y/N] " _ans_pv
[[ "$_ans_pv" =~ ^[Yy] ]] && EXTRAS="${EXTRAS},parsecvision"

if [[ "$(uname -s)" == "MINGW"* ]] || [[ "$(uname -s)" == "CYGWIN"* ]] || [[ -n "${WINDIR:-}" ]]; then
    read -rp "  Install DMA/PCILeech support? (memprocfs, Windows) [y/N] " _ans_dma
    [[ "$_ans_dma" =~ ^[Yy] ]] && EXTRAS="${EXTRAS},dma"
fi

EXTRAS="${EXTRAS#,}"  # strip leading comma

# ── Build install target ─────────────────────────────────────────────────────
INSTALL_TARGET="$ACTUAL_SOURCE"
[ -n "$EXTRAS" ] && INSTALL_TARGET="$ACTUAL_SOURCE[$EXTRAS]"

echo ""
echo "  Installing dependencies..."
if [ "$DEV_MODE" = true ]; then
    # Editable install from source directory
    pip install -e "$INSTALL_TARGET" -q
else
    # Install vivian_cli as a package into the venv (pulls in httpx, prompt_toolkit)
    pip install "$INSTALL_TARGET" -q
fi

echo -e "  ${GREEN}✓${NC} Python environment ready"

# ── Step 5: Create wrapper scripts ──────────────────────────────────────────
echo -e "${BOLD}[5/6]${NC} Creating 'vivian' and 'ai' commands..."

VIVIAN_WRAPPER="$BIN_DIR/vivian"
AI_WRAPPER="$BIN_DIR/ai"

as_root tee "$VIVIAN_WRAPPER" > /dev/null << 'WRAPPER_EOF'
#!/usr/bin/env bash
# Vivian CLI wrapper — auto-generated by install.sh
# Do not edit manually. Re-run install.sh to update.

VIVIAN_HOME="${VIVIAN_HOME:-$HOME/.vivian_cli}"
VIVIAN_VENV="${VIVIAN_HOME}/venv"

# If installed system-wide
if [ -d "/opt/vivian_cli" ]; then
    VIVIAN_HOME="/opt/vivian_cli"
    VIVIAN_VENV="/opt/vivian_cli/venv"
fi

# Use virtual environment Python if available
if [ -f "$VIVIAN_VENV/bin/python" ]; then
    PYTHON="$VIVIAN_VENV/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# Preserve current working directory
VIVIAN_LAUNCH_DIR="$PWD"

# Run Vivian via the installed package (avoids sys.path / import shadowing issues)
exec "$PYTHON" -m vivian_cli.cli_main --cwd "$VIVIAN_LAUNCH_DIR" "$@"
WRAPPER_EOF

as_root cp "$VIVIAN_WRAPPER" "$AI_WRAPPER"
as_root chmod +x "$VIVIAN_WRAPPER" "$AI_WRAPPER"

echo -e "  ${GREEN}✓${NC} Wrapper scripts created:"
echo -e "    ${CYAN}$VIVIAN_WRAPPER${NC}"
echo -e "    ${CYAN}$AI_WRAPPER${NC}"

# ── Step 6: PATH check ──────────────────────────────────────────────────────
echo -e "${BOLD}[6/6]${NC} Checking PATH..."

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "  ${YELLOW}⚠${NC}  $BIN_DIR is not in your PATH."

    # Detect shell and suggest fix
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash)
            SHELL_RC="$HOME/.bashrc"
            ;;
        zsh)
            SHELL_RC="$HOME/.zshrc"
            ;;
        fish)
            SHELL_RC="$HOME/.config/fish/config.fish"
            ;;
        *)
            SHELL_RC="$HOME/.profile"
            ;;
    esac

    echo ""
    echo -e "  ${YELLOW}Add this line to ${BOLD}$SHELL_RC${NC}${YELLOW}:${NC}"
    echo -e "  ${CYAN}export PATH=\"$BIN_DIR:\$PATH\"${NC}"
    echo ""
    echo -e "  Then run: ${CYAN}source $SHELL_RC${NC}"
    echo ""

    # Offer to add automatically
    read -rp "  Add to $SHELL_RC automatically? [Y/n] " answer
    if [ "$answer" != "n" ] && [ "$answer" != "N" ]; then
        echo "" >> "$SHELL_RC"
        echo "# Added by Vivian CLI installer" >> "$SHELL_RC"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
        echo -e "  ${GREEN}✓${NC} Added to $SHELL_RC"
        echo -e "  Run: ${CYAN}source $SHELL_RC${NC} (or restart your terminal)"
    fi
else
    echo -e "  ${GREEN}✓${NC} $BIN_DIR is in PATH"
fi

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   Vivian CLI installed successfully!          ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${CYAN}vivian${NC}              Start interactive AI assistant"
echo -e "    ${CYAN}vivian -p \"hello\"${NC}   One-shot query"
echo -e "    ${CYAN}ai${NC}                  Same as vivian (alias)"
echo ""
echo -e "  ${BOLD}Pentesting tools:${NC}"
echo -e "    ${CYAN}vivian -p \"auto_pwn 10.10.10.5\"${NC}"
echo -e "    ${CYAN}vivian -p \"quick_scan 192.168.1.0/24\"${NC}"
echo ""
echo -e "  ${BOLD}Config:${NC} ${CYAN}~/.vivian/config.json${NC}"
echo -e "  ${BOLD}Install:${NC} ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "  ${YELLOW}Tip: Restart your terminal or run 'source ~/.bashrc' to use vivian now.${NC}"
echo ""
