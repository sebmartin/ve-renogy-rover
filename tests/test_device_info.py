#!/usr/bin/env python3

"""
Tests for the device_info module.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch

from ve_renogy_rover.device_info import PRODUCT_NAME, DeviceInfo


def test_default_values():
    device_info = DeviceInfo()

    assert device_info.product_name == PRODUCT_NAME
    assert device_info.custom_name == PRODUCT_NAME
    assert device_info.serial == "RNG-CTRL-RVR"
    assert device_info.firmware_version == "0.0.0"
    assert device_info.hardware_version == "0.0.0"


def test_custom_values():
    device_info = DeviceInfo(
        product_name="Custom Product",
        custom_name="My Rover",
        serial="RNG-CTRL-RVR_1234",
        firmware_version="1.2.3",
        hardware_version="2.0.0",
    )

    assert device_info.product_name == "Custom Product"
    assert device_info.custom_name == "My Rover"
    assert device_info.serial == "RNG-CTRL-RVR_1234"
    assert device_info.firmware_version == "1.2.3"
    assert device_info.hardware_version == "2.0.0"


def test_from_dict_valid():
    data = {
        "product_name": "Test Product",
        "custom_name": "Test Rover",
        "serial": "RNG-CTRL-RVR_5678",
        "firmware_version": "1.0.0",
        "hardware_version": "1.0.0",
    }

    device_info = DeviceInfo.from_dict(data)

    assert device_info.product_name == "Test Product"
    assert device_info.custom_name == "Test Rover"
    assert device_info.serial == "RNG-CTRL-RVR_5678"
    assert device_info.firmware_version == "1.0.0"
    assert device_info.hardware_version == "1.0.0"


def test_from_dict_partial():
    data = {"custom_name": "Partial Rover", "firmware_version": "2.0.0"}

    device_info = DeviceInfo.from_dict(data)

    # Should use defaults for missing fields
    assert device_info.product_name == PRODUCT_NAME
    assert device_info.custom_name == "Partial Rover"
    assert device_info.serial.startswith("RNG-CTRL-RVR_")  # Random serial
    assert device_info.firmware_version == "2.0.0"
    assert device_info.hardware_version == "0.0.0"


def test_from_dict_empty():
    device_info = DeviceInfo.from_dict({})

    assert device_info.product_name == PRODUCT_NAME
    assert device_info.custom_name == PRODUCT_NAME
    assert device_info.serial.startswith("RNG-CTRL-RVR_")  # Random serial
    assert device_info.firmware_version == "0.0.0"
    assert device_info.hardware_version == "0.0.0"


def test_from_dict_extra_fields():
    data = {"custom_name": "Test Rover", "extra_field": "should be ignored", "another_field": 123}

    device_info = DeviceInfo.from_dict(data)

    assert device_info.custom_name == "Test Rover"
    # Should not have the extra fields
    assert not hasattr(device_info, "extra_field")
    assert not hasattr(device_info, "another_field")


def test_to_dict():
    device_info = DeviceInfo(
        custom_name="Test Rover", serial="RNG-CTRL-RVR_1234", firmware_version="1.0.0", hardware_version="1.0.0"
    )

    result = device_info.to_dict()

    expected = {
        "serial": "RNG-CTRL-RVR_1234",
        "firmware_version": "1.0.0",
        "hardware_version": "1.0.0",
        "custom_name": "Test Rover",
    }

    assert result == expected


def test_from_file_existing():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "custom_name": "File Rover",
                "serial": "RNG-CTRL-RVR_9999",
                "firmware_version": "3.0.0",
                "hardware_version": "3.0.0",
            },
            f,
        )
        temp_file = f.name

    try:
        device_info = DeviceInfo.from_file(temp_file)

        assert device_info.custom_name == "File Rover"
        assert device_info.serial == "RNG-CTRL-RVR_9999"
        assert device_info.firmware_version == "3.0.0"
        assert device_info.hardware_version == "3.0.0"
    finally:
        os.unlink(temp_file)


def test_from_file_nonexistent():
    device_info = DeviceInfo.from_file("/nonexistent/file.json")

    # Should return default values
    assert device_info.product_name == PRODUCT_NAME
    assert device_info.custom_name == PRODUCT_NAME
    assert device_info.serial == "RNG-CTRL-RVR"
    assert device_info.firmware_version == "0.0.0"
    assert device_info.hardware_version == "0.0.0"


def test_from_file_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("invalid json content")
        temp_file = f.name

    try:
        device_info = DeviceInfo.from_file(temp_file)

        # Should return default values
        assert device_info.product_name == PRODUCT_NAME
        assert device_info.custom_name == PRODUCT_NAME
        assert device_info.serial == "RNG-CTRL-RVR"
        assert device_info.firmware_version == "0.0.0"
        assert device_info.hardware_version == "0.0.0"
    finally:
        os.unlink(temp_file)


def test_to_file():
    device_info = DeviceInfo(
        custom_name="Save Rover", serial="RNG-CTRL-RVR_8888", firmware_version="4.0.0", hardware_version="4.0.0"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "test", "device.json")

        device_info.to_file(temp_file)

        # Verify file was created
        assert os.path.exists(temp_file)

        # Read and verify content
        with open(temp_file, "r") as f:
            data = json.load(f)

        expected = {
            "serial": "RNG-CTRL-RVR_8888",
            "firmware_version": "4.0.0",
            "hardware_version": "4.0.0",
            "custom_name": "Save Rover",
        }

        assert data == expected


@patch("ve_renogy_rover.device_info.logging")
def test_update_from_device_success(mock_logging):
    mock_rover = Mock()
    mock_rover.product_model.return_value = "RNG-CTRL-RVR"
    mock_rover.serial_number.return_value = "12345"
    mock_rover.software_version.return_value = "5.0.0"
    mock_rover.hardware_version.return_value = "5.0.0"

    device_info = DeviceInfo()
    device_info.update_from_device(mock_rover)

    assert device_info.serial == "RNG-CTRL-RVR_12345"
    assert device_info.firmware_version == "5.0.0"
    assert device_info.hardware_version == "5.0.0"

    # Should not log any warnings
    mock_logging.warning.assert_not_called()


@patch("ve_renogy_rover.device_info.logging")
def test_update_from_device_product_serial_exception(mock_logging):
    mock_rover = Mock()
    mock_rover.product_model.side_effect = Exception("Connection error")
    mock_rover.serial_number.side_effect = Exception("Connection error")
    mock_rover.software_version.return_value = "5.0.0"
    mock_rover.hardware_version.return_value = "5.0.0"

    device_info = DeviceInfo()
    original_serial = device_info.serial
    device_info.update_from_device(mock_rover)

    # Should keep original serial
    assert device_info.serial == original_serial
    assert device_info.firmware_version == "5.0.0"
    assert device_info.hardware_version == "5.0.0"

    # Should log warning
    mock_logging.warning.assert_called_once()


@patch("ve_renogy_rover.device_info.logging")
def test_update_from_device_firmware_exception(mock_logging):
    mock_rover = Mock()
    mock_rover.product_model.return_value = "RNG-CTRL-RVR"
    mock_rover.serial_number.return_value = "12345"
    mock_rover.software_version.side_effect = Exception("Firmware error")
    mock_rover.hardware_version.return_value = "5.0.0"

    device_info = DeviceInfo()
    original_firmware = device_info.firmware_version
    device_info.update_from_device(mock_rover)

    assert device_info.serial == "RNG-CTRL-RVR_12345"
    assert device_info.firmware_version == original_firmware
    assert device_info.hardware_version == "5.0.0"

    # Should log warning
    mock_logging.warning.assert_called_once()


@patch("ve_renogy_rover.device_info.logging")
def test_update_from_device_hardware_exception(mock_logging):
    mock_rover = Mock()
    mock_rover.product_model.return_value = "RNG-CTRL-RVR"
    mock_rover.serial_number.return_value = "12345"
    mock_rover.software_version.return_value = "5.0.0"
    mock_rover.hardware_version.side_effect = Exception("Hardware error")

    device_info = DeviceInfo()
    original_hardware = device_info.hardware_version
    device_info.update_from_device(mock_rover)

    assert device_info.serial == "RNG-CTRL-RVR_12345"
    assert device_info.firmware_version == "5.0.0"
    assert device_info.hardware_version == original_hardware

    # Should log warning
    mock_logging.warning.assert_called_once()
