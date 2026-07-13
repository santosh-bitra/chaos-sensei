#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="chaos-sensei"
REPO_URL="${CHAOS_SENSEI_REPO_URL:-https://github.com/chaos-sensei/chaos-sensei.git}"
INSTALL_DIR="${CHAOS_SENSEI_INSTALL_DIR:-$HOME/.chaos-sensei}"
BIN_DIR="${CHAOS_SENSEI_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_DIR/.venv"

info() {
  printf "\033[1;34m[INFO]\033[0m %s\n" "$1"
}

warn() {
  printf "\033[1;33m[WARN]\033[0m %s\n" "$1"
}

err() {
  printf "\033[1;31m[ERROR]\033[0m %s\n" "$1"
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Required command not found: $1"
    exit 1
  fi
}

optional_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    warn "Optional command not found: $1"
  fi
}

detect_shell_profile() {
  case "${SHELL:-}" in
    */zsh)
      echo "$HOME/.zshrc"
      ;;
    */bash)
      if [[ -f "$HOME/.bashrc" ]]; then
        echo "$HOME/.bashrc"
      else
        echo "$HOME/.bash_profile"
      fi
      ;;
    *)
      echo "$HOME/.profile"
      ;;
  esac
}

info "Installing $PROJECT_NAME"

need_cmd git
need_cmd python3

optional_cmd kubectl
optional_cmd helm
optional_cmd terraform
optional_cmd docker

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

if [[ -d "$INSTALL_DIR/.git" ]]; then
  info "Existing installation found. Pulling latest changes."
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Cloning repository into $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

info "Creating Python virtual environment"
python3 -m venv "$VENV_DIR"

info "Upgrading pip"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null

info "Installing package"
"$VENV_DIR/bin/pip" install -e "$INSTALL_DIR" >/dev/null

info "Creating executable wrapper"

cat > "$BIN_DIR/chaos-sensei" <<'EOF_WRAPPER'
#!/usr/bin/env bash
exec "VENV_DIR/bin/python" -m chaos_sensei.cli "$@"
EOF_WRAPPER

# Substitute VENV_DIR
sed -i "s|VENV_DIR|$VENV_DIR|g" "$BIN_DIR/chaos-sensei"

chmod +x "$BIN_DIR/chaos-sensei"

PROFILE_FILE="$(detect_shell_profile)"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  warn "$BIN_DIR is not currently in PATH."

  if [[ -w "$PROFILE_FILE" || ! -e "$PROFILE_FILE" ]]; then
    {
      echo ""
      echo "# Added by chaos-sensei installer"
      echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    } >> "$PROFILE_FILE"

    info "Added $BIN_DIR to PATH in $PROFILE_FILE"
    warn "Run: source $PROFILE_FILE"
  else
    warn "Could not update $PROFILE_FILE automatically."
    warn "Add this manually:"
    warn "export PATH=\"$BIN_DIR:\$PATH\""
  fi
fi

info "Verifying installation"

if "$BIN_DIR/chaos-sensei" --help >/dev/null 2>&1; then
  info "$PROJECT_NAME installed successfully."
else
  err "Installation completed, but verification failed."
  exit 1
fi

cat <<'NEXT_STEPS'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next steps:

  cd your-infra-repo
  chaos-sensei init
  chaos-sensei scan .
  chaos-sensei plan --env staging

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Important safety reminder:

  By default, chaos-sensei should NOT run against production.
  Always review chaos-sensei.yaml before starting any experiment.
  Read SECURITY.md for critical safety guidelines.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Documentation: https://github.com/chaos-sensei/chaos-sensei

NEXT_STEPS
