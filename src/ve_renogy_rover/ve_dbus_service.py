import sys

from ve_renogy_rover.dbus_service import DbusService


def create_ve_dbus_service(servicename) -> DbusService:
    sys.path.insert(1, "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python")
    from vedbus import VeDbusService  # type: ignore

    return VeDbusService(servicename, register=False)
