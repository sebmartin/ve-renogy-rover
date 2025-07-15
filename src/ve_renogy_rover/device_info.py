import json
import logging
import os
from dataclasses import dataclass
from random import randrange

from pyrover.renogy_rover import RenogyRoverController as Rover

PRODUCT_NAME = "Renogy Rover MPPT"


@dataclass
class DeviceInfo:
    product_name: str = PRODUCT_NAME
    custom_name: str = PRODUCT_NAME
    serial: str = "RNG-CTRL-RVR"
    firmware_version: str = "0.0.0"
    hardware_version: str = "0.0.0"

    @staticmethod
    def from_file(path: str) -> "DeviceInfo":
        """Load DeviceInfo from a JSON file."""
        try:
            with open(path, "r") as f:
                return DeviceInfo.from_dict(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return DeviceInfo()

    @staticmethod
    def from_dict(data: dict) -> "DeviceInfo":
        """Create DeviceInfo from a dictionary."""
        args = {key: value for key, value in data.items() if key in DeviceInfo.__dataclass_fields__}
        args.setdefault("serial", f"RNG-CTRL-RVR_{randrange(1000, 9999)}")
        return DeviceInfo(**args)

    def to_file(self, path: str):
        """Save DeviceInfo to a JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Write atomically: write to a temp file then rename it
        temp_path = path + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(temp_path, path)

    def to_dict(self) -> dict:
        """Convert the DeviceInfo to a dictionary."""
        return {
            "serial": self.serial,
            "firmware_version": self.firmware_version,
            "hardware_version": self.hardware_version,
            "custom_name": self.custom_name,
        }

    def update_from_device(self, rover: Rover):
        """Update DeviceInfo from the Renogy Rover device."""
        try:
            product = rover.product_model()
            serial = rover.serial_number()
            self.serial = f"{product}_{serial}"
        except Exception:
            logging.warning("Failed to read product model andserial number, using default.")
        try:
            self.firmware_version = rover.software_version()
        except Exception:
            logging.warning("Failed to read firmware version, using default.")
        try:
            self.hardware_version = rover.hardware_version()
        except Exception:
            logging.warning("Failed to read hardware version, using default.")
