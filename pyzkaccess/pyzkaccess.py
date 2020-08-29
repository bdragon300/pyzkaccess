import ctypes
from datetime import datetime
from typing import Iterable, Union

from .enum import ControlOperation, RelayGroup


class ZKModel:
    """Base class for concrete ZK model"""
    name = None
    relays = None
    relays_def = None
    groups_def = None


class ZK400(ZKModel):
    """ZKAccess C3-400 model"""
    name = 'C3-400'
    relays = 8
    relays_def = (
        1, 2, 3, 4,
        1, 2, 3, 4
    )
    groups_def = (
        RelayGroup.aux, RelayGroup.aux, RelayGroup.aux, RelayGroup.aux,
        RelayGroup.lock, RelayGroup.lock, RelayGroup.lock, RelayGroup.lock
    )


class ZK200(ZKModel):
    """ZKAccess C3-200"""
    name = 'C3-200'
    relays = 4
    relays_def = (1, 2, 1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.aux, RelayGroup.lock, RelayGroup.lock)


class ZK100(ZKModel):
    """ZKAccess C3-100"""
    name = 'C3-100'
    relays = 2
    relays_def = (1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.lock)


class ZKSDK:
    def __init__(self, dllpath: str):
        self.dll = ctypes.WinDLL(dllpath)
        self.handle = None

    @property
    def is_connected(self):
        return bool(self.handle is not None)

    def connect(self, connstr: bytes):
        self.handle = self.dll.Connect(connstr)
        if self.handle == 0:
            self.handle = None
            raise ConnectionError("Unable to connect device using connstr '{}'".format(connstr))

    def disconnect(self):
        if not self.handle:
            return

        self.dll.Disconnect(self.handle)
        self.handle = None

    def control_device(self, operation, p1, p2, p3, p4, options_str='') -> int:
        """
        Device control machinery method. Read PULL SDK docs for
         parameters meaning
        :param operation: Number, operation id
        :param p1: Number, depends on operation id
        :param p2: Number, depends on operation id
        :param p3: Number, depends on operation id
        :param p4: Number, depends on operation id
        :param options_str: String, depends on operation id
        :raises RuntimeError: if operation was failed
        :return: dll function result code, 0 or positive number
        """
        res = self.dll.ControlDevice(
            self.handle,
            operation,
            p1,
            p2,
            p3,
            p4,
            options_str
        )
        if res < 0:
            raise RuntimeError('ControlDevice failed, params: ({}), returned: {}'.format(
                ','.join((str(self.handle), str(operation), str(p1), str(p2), str(p3), str(p4), str(options_str))),
                str(res)
            ))

        return res

    def get_rt_log(self, buffer_size) -> str:
        """
        Machinery method for retrieving events from device.
        :param buffer_size: Required. Buffer size in bytes that filled
         with contents
        :raises RuntimeError: if operation was failed
        :return: raw string with events
        """
        buf = ctypes.create_string_buffer(buffer_size)

        res = self.dll.GetRTLog(self.handle, buf, buffer_size)
        if res < 0:
            raise RuntimeError('GetRTLog failed, returned: {}'.format(str(res)))

        return buf.value.decode('utf-8')

    def __del__(self):
        self.disconnect()


class ZKAccess:
    """Main class to work with a device.
    Holds a connection and provides interface to PULL SDK functions
    """
    def __init__(self,
                 dllpath: str = 'plcommpro.dll',
                 connstr: bytes = None,
                 device_model: ZKModel = ZK400):
        """
        :param dllpath: Full path to plcommpro.dll
        :param connstr: Device connection string. If given then
         automatically connect to a device
        :param device_model: Device model class. Default is C3-400
        """
        self.connstr = connstr
        self.device_model = device_model
        self.sdk = ZKSDK(dllpath)

        if connstr:
            self.connect(connstr)

    @property
    def dll_object(self) -> ctypes.WinDLL:
        """DLL object (`ctypes.WinDLL`). Read only."""
        return self.sdk.dll

    @property
    def handle(self):
        """Device handle. `None` if there is no active connection.
        Read only.
        """
        return self.sdk.handle

    @property
    def relays(self) -> 'RelayList':
        """Set of all relays"""
        mdl = self.device_model
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        return RelayList(sdk=self.sdk, relays=relays)

    def __enter__(self):
        if not self.sdk.is_connected:
            self.connect(self.connstr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sdk.is_connected:
            self.disconnect()

    def connect(self, connstr: bytes) -> None:
        """
        Connect to a device using connection string, ex:
        'protocol=TCP,ipaddress=192.168.22.201,port=4370,timeout=4000,passwd='
        :param connstr: device connection string
        :raises RuntimeError: if we are already connected
        :raises ConnectionError: connection attempt was failed
        :return:
        """
        if self.sdk.is_connected:
            raise RuntimeError('Already connected')

        self.connstr = connstr
        self.sdk.connect(connstr)

    def disconnect(self) -> None:
        """Disconnect from a device"""
        self.sdk.disconnect()

    def restart(self) -> None:
        """Restart a device"""
        self.sdk.control_device(ControlOperation.restart, 0, 0, 0, 0)

    def read_events(self, buffer_size=4096):
        """
        Read events from the device
        :param buffer_size:
        :return:
        """
        raw = self.sdk.get_rt_log(buffer_size)
        *events_s, empty = raw.split('\r\n')

        return (ZKRealtimeEvent(s) for s in events_s)


class Relay:
    """Concrete relay"""
    def __init__(self, sdk: ZKSDK, group: RelayGroup, number: int):
        self.sdk = sdk
        self.group = group
        self.number = number

    def switch_on(self, timeout: int) -> None:
        """
        Switch on a relay for the given time. If a relay is already
        switched on then its timeout will be refreshed
        :param timeout: Timeout in seconds while relay will be enabled.
         Number between 0 and 255
        :return:
        """
        if timeout < 0 or timeout > 255:
            raise ValueError("Incorrect timeout: {}".format(timeout))

        self.sdk.control_device(
            ControlOperation.output,
            self.number,
            self.group.value,
            timeout,
            0
        )

    def __str__(self):
        return "Relay.{}({})".format(self.group.name, self.number)

    def __repr__(self):
        return "Relay(RelayGroup.{}, {})".format(self.group.name, self.number)


class RelayList(list):
    """Collection of relay objects which is used to perform group
    operations over multiple relays
    """
    def __init__(self, sdk: ZKSDK, relays: Iterable[Relay] = ()):
        """
        :param sdk: ZKAccess object
        """
        super().__init__(relays)
        self.sdk = sdk

    def switch_on(self, timeout: int) -> None:
        """
        Switch on all relays in set
        :param timeout: Timeout in seconds while relay will be enabled.
         Number between 0 and 255
        :return:
        """
        if timeout < 0 or timeout > 255:
            raise ValueError("Timeout must be in range 0..255, got {}".format(timeout))

        if timeout < 0 or timeout > 255:
            raise ValueError("Incorrect timeout: {}".format(timeout))

        for relay in self:
            self.sdk.control_device(ControlOperation.output,
                                    relay.number,
                                    relay.group.value,
                                    timeout,
                                    0)

    @property
    def aux(self) -> 'RelayList':
        """Return relays only from aux group"""
        relays = [x for x in self if x.group == RelayGroup.aux]
        return self.__class__(sdk=self.sdk, relays=relays)

    @property
    def lock(self) -> 'RelayList':
        """Return relays only from lock group"""
        relays = [x for x in self if x.group == RelayGroup.lock]
        return self.__class__(sdk=self.sdk, relays=relays)

    def by_mask(self, mask: Iterable[Union[int, bool]]):
        relays = [x for x, m in zip(self, mask) if m]
        return self.__class__(sdk=self.sdk, relays=relays)


class ZKRealtimeEvent:
    """
    Represents one realtime event occured on the device
    Since the device returns event as string we need to parse it to the structured view. This class does this.
    """
    __slots__ = (
        'time',
        'pin',
        'card',
        'door',
        'event_type',
        'entry_exit',
        'verify_mode'
    )

    def __init__(self, s=None):
        """
        :param s: Optional. Event string to be parsed.
        """
        if s:
            self.parse(s)

    def parse(self, s):
        """
        Parse one event string and fills out slots
        :param s: event string
        :raises ValueError: event string is invalid
        :return:
        """
        if s == '' or s == '\r\n':
            raise ValueError("Empty event string")

        items = s.split(',')
        if len(items) != 7:
            raise ValueError("Event string has not 7 comma-separated parts")

        items[0] = datetime.strptime(items[0], '%Y-%m-%d %H:%M:%S')
        for i in range(len(self.__slots__)):
            setattr(self, self.__slots__[i], items[i])
