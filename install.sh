#!/bin/bash
set -e

DRIVER_NAME="ve_renogy_rover"
DEVICE_CLASS="renogy_rover"
DRIVER_SYMLINK="/opt/victronenergy/dbus.${DRIVER_NAME}"

DEFAULT_USB_IDS=("067b:2303")  # Override with --usb-id
USB_IDS=("${DEFAULT_USB_IDS[@]}")

CONF_DIR="/data/conf/serial-starter.d"
CONF_FILE="${CONF_DIR}/20-${DEVICE_CLASS}.conf"
UDEV_RULES="/etc/udev/rules.d/serial-starter.rules"
RC_LOCAL="/data/rc.local"

DRIVER_DIR="$(cd "$(dirname "$0")" && pwd)"
VERBOSE=false
DRYRUN=false
MODE="install"

log() { $VERBOSE && echo "$@"; }
run() { $DRYRUN && echo "[dry-run] $@" || eval "$@"; }

print_usage() {
  echo "Usage: $0 [--install|--uninstall|--list-devices] [--dry-run] [--verbose] [--usb-id VID:PID]"
}

validate_usb_id() {
  [[ "$1" =~ ^[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$ ]] || {
    echo "Invalid USB ID: $1"; exit 1;
  }
}

list_devices() {
  echo "🔌 Connected USB serial devices:"
  for tty in /dev/ttyUSB*; do
    [[ -e "$tty" ]] || continue
    info=$(udevadm info --query=property --name="$tty")
    vid=$(echo "$info" | grep ^ID_VENDOR_ID= | cut -d= -f2)
    pid=$(echo "$info" | grep ^ID_MODEL_ID= | cut -d= -f2)
    model=$(echo "$info" | grep ^ID_MODEL= | cut -d= -f2)
    serial=$(echo "$info" | grep ^ID_SERIAL_SHORT= | cut -d= -f2)
    echo "$tty - ID_MODEL=\"${model}\" [ID_VENDOR_ID=${vid} ID_MODEL_ID=${pid} ID_SERIAL_SHORT=\"${serial})\"]"
  done
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --install) MODE="install" ;;
    --uninstall) MODE="uninstall" ;;
    --list-devices) MODE="list" ;;
    --dry-run) DRYRUN=true ;;
    --verbose) VERBOSE=true ;;
    --usb-id) shift; validate_usb_id "$1"; USB_IDS=("$1") ;;
    -h|--help) print_usage; exit 0 ;;
    *) echo "Unknown option: $1"; print_usage; exit 1 ;;
  esac
  shift
done

install_driver() {
  echo "📦 Installing $DRIVER_NAME"

  run pip3 install .

  run mkdir -p /opt/victronenergy
  run ln -sf "$DRIVER_DIR" "$DRIVER_SYMLINK"
  run chmod +x "$DRIVER_DIR/run"

  run mkdir -p "$CONF_DIR"
  {
    echo "service ${DEVICE_CLASS} dbus.${DRIVER_NAME}"
  } | run tee "$CONF_FILE" > /dev/null

  for id in "${USB_IDS[@]}"; do
    vendor="${id%%:*}"
    product="${id##*:}"
    # ACTION=="add", ENV{ID_BUS}=="usb", ENV{ID_MODEL}=="USB-Serial_Controller", ENV{VE_SERVICE}="ignore"
    rule="SUBSYSTEM==\"tty\", ATTRS{ID_VENDOR_ID}==\"$vendor\", ATTRS{ID_MODEL_ID}==\"$product\", ENV{VE_DEVICE_CLASS}=\"${DEVICE_CLASS}\""
    if ! grep -qF "$rule" "$UDEV_RULES" 2>/dev/null; then
      echo "$rule" | run tee -a "$UDEV_RULES" > /dev/null
    fi
  done

  if [ ! -f "$RC_LOCAL" ]; then
    run "echo '#!/bin/sh' > \"$RC_LOCAL\""
    run chmod +x "$RC_LOCAL"
  fi
  grep -qF "$DRIVER_SYMLINK" "$RC_LOCAL" || run "echo 'ln -sf \"$DRIVER_DIR\" \"$DRIVER_SYMLINK\"' >> \"$RC_LOCAL\""

  echo "✅ Uninstall complete."
  echo "🔁 Please reboot the system to activate the serial-starter configuration."
}

uninstall_driver() {
  echo "🧹 Uninstalling $DRIVER_NAME"
  run rm -f "$DRIVER_SYMLINK"
  run rm -f "$CONF_FILE"
  [ -f "$UDEV_RULES" ] && run sed -i "/VE_DEVICE_CLASS\\s*=\\s*\\\"${DEVICE_CLASS}\\\"/d" "$UDEV_RULES"
  [ -f "$RC_LOCAL" ] && run sed -i "/${DRIVER_SYMLINK}/d" "$RC_LOCAL"

  echo "✅ Uninstall complete."
  echo "🔁 Please reboot the system to fully unload the serial-starter configuration."
}

case "$MODE" in
  install) install_driver ;;
  uninstall) uninstall_driver ;;
  list) list_devices ;;
  *) echo "Unknown mode: $MODE"; exit 1 ;;
esac
