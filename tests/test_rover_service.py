#!/usr/bin/env python3

"""
Tests for the rover_service module.
"""

from unittest.mock import ANY, Mock, call, patch

import pytest
from pyrover.types import ChargingState

from ve_renogy_rover import rover_service as rover_service_module
from ve_renogy_rover.dbus_service import DbusService
from ve_renogy_rover.rover_service import (
    CUSTOM_PRODUCT_ID,
    SETTINGS_PATH,
    UPDATE_INTERVAL,
    VERSION,
    OperationMode,
    RoverService,
    State,
    service_name,
)


@pytest.fixture(autouse=True)
def mock_device_info_class(mock_device_info):
    """Fixture providing a mock DeviceInfo class with from_file method."""
    with patch("ve_renogy_rover.rover_service.DeviceInfo") as mock_class:
        mock_class.from_file.return_value = mock_device_info
        yield mock_class


@pytest.fixture(autouse=True)
def mock_rover_class(mock_rover):
    """Fixture providing a mock Rover class."""
    with patch("ve_renogy_rover.rover_service.Rover") as mock_class:
        mock_class.return_value = mock_rover
        yield mock_class


@pytest.fixture(autouse=True)
def mock_dbus_service(mock_dbus_context):
    """Fixture providing a mock DBus service with context manager."""
    service = Mock(spec=DbusService)
    service.__enter__ = Mock(return_value=mock_dbus_context)
    service.__exit__ = Mock(return_value=None)
    service.add_path = Mock()
    service.register = Mock()
    return service


@pytest.fixture(autouse=True)
def mock_timeout_add():
    """Fixture providing a mock timeout add function."""
    return Mock(return_value=123)


@pytest.fixture
def rover_service(mock_device_info_class, mock_rover_class, mock_dbus_service, mock_timeout_add):
    """Fixture providing a basic RoverService instance for testing."""
    return RoverService(tty="/dev/ttyUSB1", dbus_service=mock_dbus_service, timeout_add_func=mock_timeout_add)


class TestServiceName:

    def test_service_name_with_full_path(self):
        result = service_name("/dev/ttyUSB0")
        assert result == "com.victronenergy.solarcharger.ttyUSB0"

    def test_service_name_with_just_name(self):
        result = service_name("ttyUSB1")
        assert result == "com.victronenergy.solarcharger.ttyUSB1"

    def test_service_name_with_different_device(self):
        result = service_name("/dev/ttyACM0")
        assert result == "com.victronenergy.solarcharger.ttyACM0"


class TestOperationMode:

    @pytest.mark.parametrize(
        "charging_state,expected",
        [
            (ChargingState.DEACTIVATED, OperationMode.OFF),
            (ChargingState.CURRENT_LIMITING, OperationMode.LIMITING),
            (ChargingState.MPPT, OperationMode.TRACKING),
            (None, None),
            (ChargingState.BOOST, None),
        ],
    )
    def test_from_rover(self, charging_state, expected):
        result = OperationMode.from_rover(charging_state)
        assert result == expected


class TestState:

    @pytest.mark.parametrize(
        "charging_state,expected",
        [
            (ChargingState.DEACTIVATED, State.OFF),
            (ChargingState.BOOST, State.BULK),
            (ChargingState.FLOATING, State.FLOAT),
            (ChargingState.EQUALIZING, State.EQUALIZE),
            (None, None),
            (ChargingState.MPPT, None),
        ],
    )
    def test_from_rover(self, charging_state, expected):
        result = State.from_rover(charging_state)
        assert result == expected


class TestRoverService:

    def test_init(self, mock_device_info_class, mock_rover_class, mock_dbus_service, mock_timeout_add):
        service = RoverService(tty="/dev/ttyUSB0", dbus_service=mock_dbus_service, timeout_add_func=mock_timeout_add)

        # Verify the service was initialized correctly
        assert service.tty == "/dev/ttyUSB0"
        assert service._dbus_service == mock_dbus_service
        assert service._timeout_add == mock_timeout_add

        # Verify the device info was loaded
        mock_device_info_class.from_file.assert_called_once()

        # Verify the timeout was added
        mock_timeout_add.assert_called_once_with(UPDATE_INTERVAL, service._update_path_values)

        # Verify the service was registered
        mock_dbus_service.register.assert_called_once()

    def test_tty_property(self, rover_service):
        assert rover_service.tty == "/dev/ttyUSB1"

    @pytest.mark.parametrize(
        "tty,expected",
        [
            ("/dev/ttyUSB0", 0),
            ("/dev/ttyUSB1", 1),
            ("/dev/ttyUSB10", 10),
            ("ttyUSB0", 0),
            ("ttyUSB1", 1),
        ],
    )
    def test_usb_number_property_valid(self, tty, expected, mock_dbus_service, mock_timeout_add):
        service = RoverService(tty, mock_dbus_service, mock_timeout_add)
        assert service.usb_number == expected

    @pytest.mark.parametrize(
        "tty",
        [
            "/dev/ttyACM0",
            "/dev/ttyS0",
            "invalid",
            "/dev/ttyUSB",
            "/dev/ttyUSBa",
        ],
    )
    def test_usb_number_property_invalid(self, tty, mock_dbus_service, mock_timeout_add):
        with pytest.raises(ValueError, match=f"Unsupported TTY name: {tty}"):
            RoverService(tty, mock_dbus_service, mock_timeout_add)

    def test_service_name_property(self, rover_service):
        expected = "com.victronenergy.solarcharger.ttyUSB1"
        assert rover_service.service_name == expected

    def test_connection_property(self, rover_service):
        expected = "Renogy Rover MPPT on USB1"
        assert rover_service.connection == expected

    def test_device_instance_property(self, rover_service):
        assert rover_service.device_instance == 289  # 2881

    def test_device_instance_property_caching(self, rover_service):
        # First call should set the instance
        instance1 = rover_service.device_instance
        assert instance1 == 289

        # Change the tty and verify that the instance is not updated (cached)
        rover_service._tty = "/dev/ttyUSB0"
        instance2 = rover_service.device_instance
        assert instance2 == instance1

    def test_rover_property(self, mock_rover_class, rover_service):
        rover = rover_service.rover

        assert rover == mock_rover_class.return_value
        mock_rover_class.assert_called_once_with(address=1, port="/dev/ttyUSB1")

    def test_rover_property_caching(self, mock_rover_class, rover_service):
        r1 = rover_service.rover
        r2 = rover_service.rover

        assert id(r1) == id(r2)
        mock_rover_class.assert_called_once()

    def test_register_dbus_service(self, mock_device_info_class, rover_service):
        # Check that all expected add_path calls were made
        add_path_calls = {
            call_arg[0][0]: call_arg[0][1] for call_arg in rover_service._dbus_service.add_path.call_args_list
        }
        assert add_path_calls == {
            "/Mgmt/ProcessName": rover_service_module.__file__,
            "/Mgmt/ProcessVersion": VERSION,
            "/Mgmt/Connection": "Renogy Rover MPPT on USB1",
            "/DeviceInstance": 289,
            "/ProductId": CUSTOM_PRODUCT_ID,
            "/ProductName": mock_device_info_class.from_file.return_value.product_name,
            "/CustomName": mock_device_info_class.from_file.return_value.custom_name,
            "/Serial": mock_device_info_class.from_file.return_value.serial,
            "/FirmwareVersion": mock_device_info_class.from_file.return_value.firmware_version,
            "/HardwareVersion": mock_device_info_class.from_file.return_value.hardware_version,
            "/Connected": 1,
            "/NrOfTrackers": 1,
            "/Mode": 1,
            "/ErrorCode": 0,
            "/DeviceOffReason": 0,
            "/Pv/V": 0,
            "/Pv/I": 0,
            "/Yield/Power": 0,
            "/Dc/0/Voltage": 0,
            "/Dc/0/Current": 0,
            "/Link/TemperatureSense": 0,
            "/Link/TemperatureSenseActive": True,
            "/History/Daily/0/Yield": 0,
            "/History/Daily/0/MaxPower": 0,
            "/History/Daily/0/Pv/0/Yield": 0,
            "/History/Daily/0/Pv/0/MaxPower": 0,
            "/MppOperationMode": 0,
            "/State": 0,
        }

        # Verify the timeout was added
        rover_service._timeout_add.assert_called_once_with(UPDATE_INTERVAL, rover_service._update_path_values)

        # Verify the service was registered
        rover_service._dbus_service.register.assert_called_once()

    def test_update_path_values_success(self, rover_service, mock_rover):
        rover_service._rover = mock_rover

        # Call the update method
        result = rover_service._update_path_values()

        assert result is True

        # Verify that the context manager was used
        rover_service._dbus_service.__enter__.assert_called_once()
        rover_service._dbus_service.__exit__.assert_called_once()

        # Verify that values were set in the context
        context = rover_service._dbus_service.__enter__.return_value
        update_calls = {call[0][0]: call[0][1] for call in context.__setitem__.call_args_list}
        assert update_calls == {
            "/Pv/V": 24.5,
            "/Pv/I": 2.1,
            "/Yield/Power": 24.5 * 2.1,  # solar_voltage * charging_current
            "/Dc/0/Voltage": 12.8,
            "/Dc/0/Current": 50.0 / 12.8,  # charging_power / battery_voltage
            "/Link/TemperatureSense": 25.0,
            "/History/Daily/0/Yield": 1.2,
            "/History/Daily/0/MaxPower": 50.0,  # max_charging_power_today / 1000
            "/History/Daily/0/Pv/0/Yield": 1.2,
            "/History/Daily/0/Pv/0/MaxPower": 50.0,  # max_charging_power_today / 1000
            "/MppOperationMode": OperationMode.TRACKING.value,
            # Note: /State is not updated because ChargingState.MPPT doesn't map to any State enum value
        }

    def test_update_path_values_with_exceptions(self, rover_service, mock_rover):
        # Update only the properties that need to change for this test
        mock_rover.solar_voltage.side_effect = Exception("Connection error")
        mock_rover.charging_current.side_effect = Exception("Connection error")
        mock_rover.charging_power.side_effect = Exception("Connection error")
        mock_rover.battery_voltage.side_effect = Exception("Connection error")
        mock_rover.battery_temperature.side_effect = Exception("Sensor error")
        mock_rover.charging_state.side_effect = Exception("Connection error")
        mock_rover.max_charging_power_today.side_effect = Exception("Connection error")
        mock_rover.power_generation_today.side_effect = Exception("Connection error")
        mock_rover.max_charging_power_today.side_effect = Exception("Connection error")

        rover_service._rover = mock_rover

        # Call the update method
        result = rover_service._update_path_values()

        assert result is True

        # There should be no updates when there are exceptions
        context = rover_service._dbus_service.__enter__.return_value
        update_calls = {call[0][0]: call[0][1] for call in context.__setitem__.call_args_list}
        assert update_calls == {}

    def test_on_custom_name_change(self, rover_service):
        # Test changing the custom name
        new_name = "New Custom Name"
        result = rover_service._on_custom_name_change("/CustomName", new_name)

        assert result is True
        assert rover_service.device_info.custom_name == new_name
        rover_service.device_info.to_file.assert_called_once_with(SETTINGS_PATH)
