#!/bin/bash
set -e

DRIVER_NAME="ve_renogy_rover"
DEFAULT_USB_IDS=("1a86:7523" "10c4:ea60")
USB_IDS=("${DEFAULT_USB_IDS[@]}")

DRIVER_DIR="$(cd "$(dirname "$0")" && pwd)"
DRIVER_SYMLINK="/opt/victronenergy/dbus.${DRIVER_NAME}"

CONF_NAME="20-${DRIVER_NAME}.conf"
CONF_PATH="/data/venus/serial-starter/usb-serial.d/${CONF_NAME}"
CONF_SYMLINK="/etc/venus/serial-starter/usb-serial.d/${CONF_NAME}"

RC_LOCAL="/data/rc.local"

VERBOSE=false
DRYRUN=false
MODE="install"

log() { $VERBOSE && echo "$@"; }
run() { $DRYRUN && echo "[dry-run] $@" || eval "$@"; }

print_usage() {
  echo "Usage: $0 [--install|--uninstall] [--dry-run] [--verbose] [--usb-id VID:PID]"
}

validate_usb_id() {
  [[ "$1" =~ ^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$ ]] || {
    echo "Invalid USB ID: $1"; exit 1;
  }
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --install) MODE="install" ;;
    --uninstall) MODE="uninstall" ;;
    --dry-run) DRYRUN=true ;;
    --verbose) VERBOSE=true ;;
    --usb-id) shift; validate_usb_id "$1"; USB_IDS=("$1") ;;
    -h|--help) print_usage; exit 0 ;;
    *) echo "Unknown option: $1"; print_usage; exit 1 ;;
  esac
  shift
done

install_driver() {
  echo "📦 Installing $DRIVER_NAME from $DRIVER_DIR"
  echo "🔍 USB ID(s): ${USB_IDS[*]}"

  run pip3 install .

  run mkdir -p /opt/victronenergy
  run ln -sf "$DRIVER_DIR" "$DRIVER_SYMLINK"

  mkdir -p "$(dirname "$CONF_PATH")"
  {
    for id in "${USB_IDS[@]}"; do
      echo "[serial-usb-ven-usb-device:${id}]"
      echo "name=serial-${DRIVER_NAME}"
      echo "driver=dbus.${DRIVER_NAME}"
      echo
    done
  } | run tee "$CONF_PATH" > /dev/null
  run ln -sf "$CONF_PATH" "$CONF_SYMLINK"

  if [ ! -f "$RC_LOCAL" ]; then
    run "echo '#!/bin/sh' > \"$RC_LOCAL\""
    run chmod +x "$RC_LOCAL"
  fi
  grep -qF "$DRIVER_SYMLINK" "$RC_LOCAL" || run "echo 'ln -sf \"$DRIVER_DIR\" \"$DRIVER_SYMLINK\"' >> \"$RC_LOCAL\""
  grep -qF "$CONF_SYMLINK" "$RC_LOCAL" || run "echo 'ln -sf \"$CONF_PATH\" \"$CONF_SYMLINK\"' >> \"$RC_LOCAL\""

  run chmod +x "$DRIVER_DIR/run"

  echo "♻️ Restarting serial-starter..."
  run sv restart serial-starter || echo "⚠️ Could not restart serial-starter. Please reboot manually."

  echo "✅ Install complete."
}

uninstall_driver() {
  echo "🧹 Uninstalling $DRIVER_NAME"
  run rm -f "$DRIVER_SYMLINK" "$CONF_PATH" "$CONF_SYMLINK"

  if [ -f "$RC_LOCAL" ]; then
    run sed -i "/${DRIVER_NAME}/d" "$RC_LOCAL"
  fi

  echo "♻️ Restarting serial-starter..."
  run sv restart serial-starter || echo "⚠️ Could not restart serial-starter. Please reboot manually."

  echo "✅ Uninstall complete."
}

case "$MODE" in
  install) install_driver ;;
  uninstall) uninstall_driver ;;
  *) echo "Unknown mode: $MODE"; exit 1 ;;
esac
