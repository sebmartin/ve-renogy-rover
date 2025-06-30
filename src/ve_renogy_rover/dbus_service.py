from typing import Any, Protocol


class DbusService(Protocol):
    """
    A protocol based on the VeDbusService class from the Victron Energy D-Bus library. This class
    comes built-in with the Victron Energy system and is used to create D-Bus services. This Protocol
    makes it easier to test and mock the DbusService in unit tests without needing the actual
    Victron Energy library.
    """

    def register(self): ...

    def __del__(self): ...

    def get_name(self): ...

    def add_path(
        self,
        path,
        value,
        description="",
        writeable=False,
        onchangecallback=None,
        gettextcallback=None,
        valuetype=None,
        itemtype=None,
    ): ...

    def add_mandatory_paths(
        self,
        processname,
        processversion,
        connection,
        deviceinstance,
        productid,
        productname,
        firmwareversion,
        hardwareversion,
        connected,
    ): ...

    def __getitem__(self, path) -> Any: ...

    def __setitem__(self, path, newvalue): ...

    def __delitem__(self, path): ...

    def __contains__(self, path) -> bool: ...

    def __enter__(self) -> "ServiceContext": ...

    def __exit__(self, *exc): ...


class ServiceContext(object):
    def __init__(self, parent): ...

    def __contains__(self, path) -> bool: ...

    def __getitem__(self, path) -> DbusService: ...

    def __setitem__(self, path, newvalue): ...

    def __delitem__(self, path): ...

    def flush(self): ...

    def add_path(self, path, value, *args, **kwargs): ...

    def del_tree(self, root): ...

    def get_name(self) -> str: ...
