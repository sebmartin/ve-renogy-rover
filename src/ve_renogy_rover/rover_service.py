#!/usr/bin/env python3

"""
Renogy MPPT example see:
https://github.com/sstoops/dbus-renogy-dcc/blob/main/dbus-renogy-dcc.py
"""

import argparse
import logging
import sys
from enum import IntEnum
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, Optional

from pyrover.renogy_rover import RenogyRoverController as Rover
from pyrover.types import ChargingState

from ve_renogy_rover.dbus_service import DbusService
from ve_renogy_rover.device_info import DeviceInfo
from ve_renogy_rover.glib_wrapper import timeout_add
from ve_renogy_rover.ve_dbus_service import create_ve_dbus_service

try:
    VERSION = version("ve-renogy-rover")  # Replace with your actual package name
except PackageNotFoundError:
    VERSION = "v0.1.0"

CUSTOM_PRODUCT_ID = 0xF102  # Custom product ID for Renogy Rover MPPT, randomly chosen
UPDATE_INTERVAL = 3000  # milliseconds
SETTINGS_PATH = "/data/renogy/rover.json"


def service_name(tty: str) -> str:
    """
    Generate a service name based on the tty name.
    e.g. /dev/ttyUSB0 -> com.victronenergy.solarcharger.ttyUSB0
    """
    name = tty.split("/")[-1]
    return f"com.victronenergy.solarcharger.{name}"


class OperationMode(IntEnum):
    OFF = 0
    LIMITING = 1
    TRACKING = 2

    @staticmethod
    def from_rover(charging_state: Optional[ChargingState]) -> Optional["OperationMode"]:
        if charging_state == ChargingState.DEACTIVATED:
            return OperationMode.OFF
        elif charging_state == ChargingState.CURRENT_LIMITING:
            return OperationMode.LIMITING
        elif charging_state == ChargingState.MPPT:
            return OperationMode.TRACKING
        return None


class State(IntEnum):
    OFF = 0
    FAULT = 2
    BULK = 3
    ABSORPTION = 4
    FLOAT = 5
    STORAGE = 6
    EQUALIZE = 7
    EXTERNAL_CONTROL = 252

    @staticmethod
    def from_rover(charging_state: Optional[ChargingState]) -> Optional["State"]:
        if charging_state == ChargingState.DEACTIVATED:
            return State.OFF
        elif charging_state == ChargingState.BOOST:
            return State.BULK
        elif charging_state == ChargingState.FLOATING:
            return State.FLOAT
        elif charging_state == ChargingState.EQUALIZING:
            return State.EQUALIZE
        return None


class RoverService(object):
    """
    A D-Bus service for the Renogy Rover MPPT solar charger to be used with Victron's Venus OS.
    This service communicates with a Renogy Rover MPPT device connected via USB and provides
    publishes information about the device such as voltage, current, and other parameters
    to the D-Bus system, allowing it to be monitored and controlled via the Victron system.
    """

    def __init__(self, tty: str, dbus_service: DbusService, timeout_add_func=None):
        self._tty = tty
        self._device_instance = None
        self._rover = None
        self._dbus_service = dbus_service
        self._timeout_add = timeout_add_func or timeout_add

        self.device_info = DeviceInfo.from_file(SETTINGS_PATH)

        self._register_dbus_service()

    @property
    def tty(self) -> str:
        """Return the tty name."""
        return self._tty

    @property
    def usb_number(self) -> int:
        """
        Return the USB number extracted from the tty name.
        e.g.
          ttyUSB0 -> 0, ttyUSB1 -> 1, etc.
          /dev/ttyUSB0 -> 0, /dev/ttyUSB1 -> 1, etc.
        """
        parts = self._tty.lower().split("ttyusb")
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
        else:
            raise ValueError(f"Unsupported TTY name: {self._tty}")

    @property
    def service_name(self) -> str:
        return service_name(self._tty)

    @property
    def connection(self) -> str:
        """
        Return the connection string for the service.
        This is used in the /Mgmt/Connection path.
        """
        return f"Renogy Rover MPPT on USB{self.usb_number}"

    @property
    def device_instance(self) -> int:
        """
        Return the device instance based on the tty name. Only supports USB for now.
          /dev/ttyUSBx: 288 + x
        """
        if self._device_instance is None:
            self._device_instance = 288 + self.usb_number
        return self._device_instance

    @property
    def rover(self) -> Rover:
        if not self._rover:
            self._rover = Rover(address=1, port=self._tty)
        return self._rover

    def _register_dbus_service(self):
        # Get a few static values from the device
        self.device_info.update_from_device(self.rover)

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbus_service.add_path("/Mgmt/ProcessName", __file__)
        self._dbus_service.add_path("/Mgmt/ProcessVersion", VERSION)
        self._dbus_service.add_path("/Mgmt/Connection", self.connection)

        # Create the mandatory objects
        self._dbus_service.add_path("/DeviceInstance", self.device_instance)
        self._dbus_service.add_path("/ProductId", CUSTOM_PRODUCT_ID)
        self._dbus_service.add_path("/ProductName", self.device_info.product_name)
        self._dbus_service.add_path(
            "/CustomName",
            self.device_info.custom_name,
            writeable=True,
            onchangecallback=self._on_custom_name_change,
        )
        self._dbus_service.add_path("/Serial", self.device_info.serial)
        self._dbus_service.add_path("/FirmwareVersion", self.device_info.firmware_version)
        self._dbus_service.add_path("/HardwareVersion", self.device_info.hardware_version)
        self._dbus_service.add_path("/Connected", 1)

        # https://github.com/victronenergy/venus/wiki/dbus#solar-chargers
        paths = {
            # Static values
            "/NrOfTrackers": 1,  # Rovers are single tracker devices
            "/Mode": 1,  # 1=On; 4=Off
            "/ErrorCode": 0,
            "/DeviceOffReason": 0,  # Bitmask indicating the reason(s) that the MPPT is in Off State
            "/Link/TemperatureSenseActive": True,
            # Dynamic values that will be updated periodically
            "/Pv/V": 0,  # Voltage in Volts, exists only for single tracker devices
            "/Pv/I": 0,  # Current in Amps, exists only for single tracker devices
            "/Yield/Power": 0,  # Power in Watts, total yield power
            "/Dc/0/Voltage": 0,  # Actual battery voltage
            "/Dc/0/Current": 0,  # Actual battery charging current
            "/Link/TemperatureSense": 0,
            "/History/Daily/0/Yield": 0,  # Today's yield in kWh
            "/History/Daily/0/MaxPower": 0,  # Today's max power in Watts
            "/MppOperationMode": OperationMode.OFF.value,  # MPPT Tracker deactivated
            "/State": State.OFF.value,  # 1=On; 4=Off
        }
        for path, initial in paths.items():
            self._dbus_service.add_path(path, initial, writeable=False)

        self._dbus_service.register()

        # Callback to update the values periodically
        self._timeout_add(UPDATE_INTERVAL, self._update_path_values)

    def _update_path_values(self):
        rover = self.rover

        def try_(func: Callable[[], Any], modifier: Callable[[Any], Any] = lambda x: x):
            try:
                return modifier(func())
            except Exception as e:
                logging.error(f"Error getting `{func.__name__}` value from rover: {e}")
                return None

        def solar_power():
            v = try_(rover.solar_voltage)
            i = try_(rover.charging_current)
            if v is None or i is None:
                return None
            return v * i

        def charging_current():
            p = try_(rover.charging_power)
            v = try_(rover.battery_voltage)
            if p and v and v > 0:
                return p / v
            return None

        try:
            updates = {
                path: value
                for path, value in {
                    "/Pv/V": try_(rover.solar_voltage),
                    "/Pv/I": try_(rover.charging_current),
                    "/Yield/Power": solar_power(),
                    "/Dc/0/Voltage": try_(rover.battery_voltage),
                    "/Dc/0/Current": charging_current(),
                    "/Link/TemperatureSense": try_(rover.battery_temperature),
                    "/History/Daily/0/Yield": try_(rover.power_generation_today),
                    "/History/Daily/0/MaxPower": try_(rover.max_charging_power_today, lambda x: x / 1000.0),
                }.items()
                if value is not None  # Don't update paths that raise an exception (if any)
            }

            charging_state = try_(rover.charging_state)
            if (operation_mode := OperationMode.from_rover(charging_state)) is not None:
                updates["/MppOperationMode"] = operation_mode.value
            else:
                logging.warning(f"Unknown operation mode for charging state: {charging_state}")

            if (state := State.from_rover(try_(rover.charging_state))) is not None:
                updates["/State"] = state.value
        except Exception as e:
            logging.exception(f"Error updating path values: {e}")
            return True

        with self._dbus_service as s:
            for path, value in updates.items():
                s[path] = value
                logging.debug(f"{path}: {s[path]}")
        return True

    def _on_custom_name_change(self, path, value):
        """
        Set the custom name for the device.
        This is a writeable path that can be changed via the dbus.
        """
        self.device_info.custom_name = value
        self.device_info.to_file(SETTINGS_PATH)
        return True


def main():
    parser = argparse.ArgumentParser(description="DBUS Driver for Renogy Rover MPPT for Venus OS")
    parser.add_argument("device", nargs="?", help="Serial device to use, e.g. /dev/ttyUSB0")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="[%(asctime)s] %(levelname)s: %(message)s")

    if not args.device:
        logging.error("No device specified. Use --help for usage.")
        sys.exit(1)

    device = args.device.strip()
    device = device if device.startswith("/") else f"/dev/{device}"

    logging.info(f"Starting driver on device: {device}")

    try:
        from dbus.mainloop.glib import DBusGMainLoop  # type: ignore

        # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
        DBusGMainLoop(set_as_default=True)

        dbus_service = create_ve_dbus_service(service_name(device))
        RoverService(tty=device, dbus_service=dbus_service, timeout_add_func=timeout_add)
        logging.info("Service initialization complete.")

        try:
            sys.path.insert(1, "/usr/lib/python3.8/site-packages")
            from gi.repository import GLib  # type: ignore

            mainloop = GLib.MainLoop()
            mainloop.run()
        except ImportError:
            logging.warning("GLib not available. Cannot run main loop.")

    except Exception as e:
        logging.error(f"Driver encountered an error: {e}")
        sys.exit(1)

    logging.info("Driver exiting cleanly")


if __name__ == "__main__":
    main()
