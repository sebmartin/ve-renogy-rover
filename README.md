# ve-renogy-rover

A D-Bus service to integrate Renogy Rover MPPT solar chargers with Victron Venus OS, enabling monitoring and control through the Victron ecosystem.

## Overview

This project provides a D-Bus driver that bridges Renogy Rover MPPT solar charge controllers with Victron's Venus OS. It provides real-time monitoring of:

- Solar panel voltage and current
- Battery voltage and charging current
- Power generation and daily yield
- Charging state and operation mode
- Temperature monitoring

## Requirements

- Renogy Rover MPPT solar charge controller
- USB-to-Serial adapter (typically Prolific PL2303)
- Victron device running Venus OS (Cerbo GX, Venus GX, etc.)
- Python 3.8+ and pip3

## Installation

### Quick Install

```bash
git clone https://github.com/sebmartin/ve-renogy-rover.git
cd ve-renogy-rover
sudo ./install.sh --install
sudo reboot
```

### Manual Install

```bash
sudo pip3 install .
sudo mkdir -p /opt/victronenergy
sudo ln -sf $(pwd) /opt/victronenergy/dbus.ve_renogy_rover
sudo chmod +x run
sudo mkdir -p /data/conf/serial-starter.d
echo "service renogy_rover dbus.ve_renogy_rover" | sudo tee /data/conf/serial-starter.d/20-renogy_rover.conf
echo 'SUBSYSTEM=="tty", ATTRS{ID_VENDOR_ID}=="067b", ATTRS{ID_MODEL_ID}=="2303", ENV{VE_DEVICE_CLASS}="renogy_rover"' | sudo tee -a /etc/udev/rules.d/serial-starter.rules
sudo reboot
```

## Usage

1. Connect your Renogy Rover MPPT via USB-to-Serial adapter
2. Power on - the driver auto-detects and starts monitoring
3. Access data through Victron interface or D-Bus

### Testing

```bash
# List connected devices
sudo ./install.sh --list-devices

# Manual test (replace with your device)
python3 -m ve_renogy_rover.rover_service /dev/ttyUSB0 --debug
```

### D-Bus Interface

The driver exposes data under `com.victronenergy.solarcharger.ttyUSBx`:

**Key Paths:**
- `/Pv/V` - Solar panel voltage (V)
- `/Pv/I` - Solar panel current (A)
- `/Yield/Power` - Total power output (W)
- `/Dc/0/Voltage` - Battery voltage (V)
- `/Dc/0/Current` - Battery charging current (A)
- `/History/Daily/0/Yield` - Today's energy yield (kWh)
- `/State` - Charging state
- `/CustomName` - User-configurable device name

## Configuration

### Custom Device Name

You can rename your device using the Venus UI and it will be persisted. It can also be updated directly through dbus:

```bash
dbus-send --system --print-reply --dest=com.victronenergy.solarcharger.ttyUSB0 \
  /CustomName com.victronenergy.BusItem.SetValue string:"My Solar Charger"
```

### Different USB Adapter

```bash
sudo ./install.sh --list-devices
sudo ./install.sh --install --usb-id YOUR_VID:YOUR_PID
```

## Troubleshooting

### Common Issues

**Device not detected:**
- Check USB connection and adapter compatibility
- Verify udev rules: `sudo ./install.sh --list-devices`
- Check logs: `tail -f /var/log/serial-starter.log`

**No data appearing:**
- Verify Renogy Rover is powered and connected
- Check driver logs: `tail -f /opt/victronenergy/dbus.ve_renogy_rover/driver.log`
- Test manually: `python3 -m ve_renogy_rover.rover_service /dev/ttyUSB0 --debug`

### Debug Mode

```bash
python3 -m ve_renogy_rover.rover_service /dev/ttyUSB0 --debug
```

## Uninstall

```bash
sudo ./install.sh --uninstall
sudo reboot
```

## Development

### Setup

```bash
pip install -e .[dev]
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- Uses [pyrover](https://github.com/sebmartin/pyrover) library
- Follows [Victron D-Bus API](https://github.com/victronenergy/venus/wiki/dbus)
