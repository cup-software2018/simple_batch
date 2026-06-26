#!/usr/bin/env bash
set -euo pipefail

INSTALL_LIB=/opt/simple_batch
INSTALL_BIN=/usr/local/bin
CONFIG_DIR=/etc/simple_batch
DATA_DIR=/var/lib/simple_batch
SERVICE=simple_batch
CMDS=(bmanager bclient bclient_gui bmon bkill)

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[install]${NC} $*"; }
warn()  { echo -e "${YELLOW}[install]${NC} $*"; }
error() { echo -e "${RED}[install]${NC} $*" >&2; exit 1; }

[ "$EUID" -ne 0 ] && error "Run as root:  sudo bash install.sh [install|remove]"

SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SRC"

# ── install ───────────────────────────────────────────────────────────────────
cmd_install() {
    command -v python3 >/dev/null 2>&1 || error "Python 3 is not installed."
    PYTHON3=$(command -v python3)
    info "Using $PYTHON3 ($(python3 --version))"

    info "Installing Python dependencies..."
    "$PYTHON3" -m pip install --quiet psutil pyyaml
    "$PYTHON3" -m pip install --quiet pyside6 \
        || warn "PySide6 not installed — bclient_gui will be unavailable."

    info "Creating directories..."
    mkdir -p "$INSTALL_LIB" "$CONFIG_DIR" "$DATA_DIR"/{job_requests,kill_requests,logs}
    chmod 1777 "$DATA_DIR/job_requests" "$DATA_DIR/kill_requests"
    chmod 755  "$DATA_DIR" "$DATA_DIR/logs"

    info "Copying library files to $INSTALL_LIB..."
    cp bjob.py config.py "$INSTALL_LIB/"

    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        info "Installing config to $CONFIG_DIR/config.yaml..."
        cp config.yaml "$CONFIG_DIR/config.yaml"
        sed -i "s|^base_dir:.*|base_dir: $DATA_DIR|" "$CONFIG_DIR/config.yaml"
    else
        warn "Config already exists at $CONFIG_DIR/config.yaml — not overwriting."
    fi

    info "Installing commands to $INSTALL_BIN..."
    for cmd in "${CMDS[@]}"; do
        cp "$cmd" "$INSTALL_LIB/$cmd"
        cat > "$INSTALL_BIN/$cmd" <<EOF
#!/usr/bin/env bash
exec env PYTHONPATH="$INSTALL_LIB" \\
         SIMPLE_BATCH_CONFIG="$CONFIG_DIR/config.yaml" \\
         "$PYTHON3" "$INSTALL_LIB/$cmd" "\$@"
EOF
        chmod 755 "$INSTALL_BIN/$cmd"
    done

    if command -v systemctl >/dev/null 2>&1; then
        info "Installing systemd service ($SERVICE.service)..."
        cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Simple Batch Manager
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_BIN/bmanager run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload
        info "Service installed. To start and enable on boot:"
        info "  systemctl start $SERVICE"
        info "  systemctl enable $SERVICE"
    else
        warn "systemd not found — skipping service installation."
        info "Start the manager manually with: bmanager start"
    fi

    echo ""
    info "Installation complete."
    printf "  %-8s %s\n" "Config:"  "$CONFIG_DIR/config.yaml"
    printf "  %-8s %s\n" "Data:"    "$DATA_DIR"
    printf "  %-8s %s\n" "Log:"     "$DATA_DIR/logs/bmanager.log"
    echo ""
    echo "Commands available to all users:"
    echo "  bmanager start | stop | restart | status"
    echo "  bclient  <name> <first_id> <last_id> <script> [args...]"
    echo "  bmon     [-w [interval]]"
    echo "  bkill    <name> <from_id> <to_id>  |  bkill 0 (kill all)"
}

# ── remove ────────────────────────────────────────────────────────────────────
cmd_remove() {
    # Stop and disable service
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
            info "Stopping $SERVICE service..."
            systemctl stop "$SERVICE"
        fi
        if systemctl is-enabled --quiet "$SERVICE" 2>/dev/null; then
            info "Disabling $SERVICE service..."
            systemctl disable "$SERVICE"
        fi
        if [ -f "/etc/systemd/system/$SERVICE.service" ]; then
            rm -f "/etc/systemd/system/$SERVICE.service"
            systemctl daemon-reload
            info "Removed systemd service."
        fi
    fi

    # Remove wrapper scripts
    info "Removing commands from $INSTALL_BIN..."
    for cmd in "${CMDS[@]}"; do
        rm -f "$INSTALL_BIN/$cmd"
    done

    # Remove library files
    if [ -d "$INSTALL_LIB" ]; then
        info "Removing $INSTALL_LIB..."
        rm -rf "$INSTALL_LIB"
    fi

    # Remove config
    if [ -d "$CONFIG_DIR" ]; then
        info "Removing $CONFIG_DIR..."
        rm -rf "$CONFIG_DIR"
    fi

    # Ask before removing data directory (contains job history / logs)
    if [ -d "$DATA_DIR" ]; then
        echo ""
        read -r -p "Remove data directory $DATA_DIR? (job history and logs will be lost) [y/N] " yn
        case "$yn" in
            [yY]*) rm -rf "$DATA_DIR"; info "Removed $DATA_DIR." ;;
            *)     warn "Kept $DATA_DIR." ;;
        esac
    fi

    echo ""
    info "Uninstallation complete."
}

# ── dispatch ──────────────────────────────────────────────────────────────────
case "${1:-install}" in
    install)          cmd_install ;;
    remove|uninstall) cmd_remove  ;;
    *)
        echo "Usage: sudo bash install.sh [install|remove]"
        echo "  install  — install simple_batch system-wide (default)"
        echo "  remove   — uninstall and clean up"
        exit 1
        ;;
esac
