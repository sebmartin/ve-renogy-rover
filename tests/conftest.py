import os
import tempfile
from typing import Any, Dict
from unittest.mock import Mock

import pytest

# Add the src directory to the path so we can import the modules
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pyrover.renogy_rover import RenogyRoverController
from pyrover.types import ChargingState

from ve_renogy_rover.dbus_service import DbusService, ServiceContext


@pytest.fixture
def mock_dbus_context():
    """Fixture providing a mock DBus context for the context manager."""
    context = Mock(spec=ServiceContext)
    context.__getitem__ = Mock(return_value=0)
    context.__setitem__ = Mock()
    return context


@pytest.fixture
def mock_dbus_service(mock_dbus_context):
    """Create a mock D-Bus service for testing."""
    service = Mock(spec=DbusService)
    service.__enter__ = Mock(return_value=mock_dbus_context)
    service.__exit__ = Mock(return_value=None)
    service.add_path = Mock()
    service.register = Mock()
    return service


@pytest.fixture
def mock_rover():
    """Create a mock Renogy Rover controller for testing."""
    rover = Mock(spec=RenogyRoverController)

    # Mock all the rover methods that return values
    rover.solar_voltage = Mock(return_value=24.5, __name__="solar_voltage")
    rover.charging_current = Mock(return_value=2.1, __name__="charging_current")
    rover.charging_power = Mock(return_value=50.0, __name__="charging_power")
    rover.battery_voltage = Mock(return_value=12.8, __name__="battery_voltage")
    rover.battery_temperature = Mock(return_value=25.0, __name__="battery_temperature")
    rover.power_generation_today = Mock(return_value=1.2, __name__="power_generation_today")
    rover.max_charging_power_today = Mock(return_value=50000, __name__="max_charging_power_today")  # 50W in mW
    rover.charging_state = Mock(return_value=ChargingState.MPPT, __name__="charging_state")
    rover.product_model = Mock(return_value="RNG-CTRL-RVR", __name__="product_model")
    rover.serial_number = Mock(return_value="12345", __name__="serial_number")
    rover.software_version = Mock(return_value="1.0.0", __name__="software_version")
    rover.hardware_version = Mock(return_value="1.0.0", __name__="hardware_version")

    return rover


@pytest.fixture
def mock_device_info():
    """Create a mock DeviceInfo for testing."""
    from ve_renogy_rover.device_info import DeviceInfo

    device_info = Mock(spec=DeviceInfo)
    device_info.product_name = "Renogy Rover MPPT"
    device_info.custom_name = "Test Rover"
    device_info.serial = "RNG-CTRL-RVR_1234"
    device_info.firmware_version = "1.0.0"
    device_info.hardware_version = "1.0.0"
    return device_info


@pytest.fixture
def mock_device_info_class(mock_device_info):
    """Fixture providing a mock DeviceInfo class with from_file method."""
    from unittest.mock import patch

    with patch("ve_renogy_rover.rover_service.DeviceInfo") as mock_class:
        mock_class.from_file.return_value = mock_device_info
        yield mock_class


@pytest.fixture
def mock_rover_class(mock_rover):
    """Fixture providing a mock Rover class."""
    from unittest.mock import patch

    with patch("ve_renogy_rover.rover_service.Rover") as mock_class:
        mock_class.return_value = mock_rover
        yield mock_class


@pytest.fixture
def mock_timeout_add():
    """Fixture providing a mock timeout add function."""
    return Mock(return_value=123)


@pytest.fixture
def temp_settings_file():
    """Create a temporary settings file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"custom_name": "Test Rover", "serial": "RNG-CTRL-RVR_1234"}')
        temp_file = f.name

    yield temp_file

    # Cleanup
    try:
        os.unlink(temp_file)
    except OSError:
        pass


@pytest.fixture
def mock_glib():
    """Mock GLib for testing."""
    glib_mock = Mock()
    glib_mock.timeout_add = Mock(return_value=123)  # Return a timer ID
    return glib_mock


@pytest.fixture
def mock_mainloop():
    """Mock GLib.MainLoop for testing."""
    mainloop_mock = Mock()
    mainloop_mock.run = Mock()
    return mainloop_mock


@pytest.fixture
def sample_rover_data() -> Dict[str, Any]:
    """Sample data that a real rover would return."""
    return {
        "solar_voltage": 24.5,
        "charging_current": 2.1,
        "charging_power": 50.0,
        "battery_voltage": 12.8,
        "battery_temperature": 25.0,
        "power_generation_today": 1.2,
        "max_charging_power_today": 50000,  # 50W in mW
        "charging_state": None,
        "product_model": "RNG-CTRL-RVR",
        "serial_number": "12345",
        "software_version": "1.0.0",
        "hardware_version": "1.0.0",
    }
