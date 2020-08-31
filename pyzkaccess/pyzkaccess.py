import ctypes
import time
from collections import deque
from datetime import datetime
from typing import Iterable, Union, Optional

from .device import ZKModel, ZK400, ZKDevice
from .enum import ControlOperation, RelayGroup
import itertools


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
            # FIXME: return errors description everywhere
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
            fmt = (
                ','.join((str(self.handle), str(operation), str(p1),
                          str(p2), str(p3), str(p4), str(options_str))),
                str(res)
            )
            raise RuntimeError('ControlDevice failed, params: ({}), returned: {}'.format(*fmt))

        return res

    def get_rt_log(self, buffer_size: int) -> Iterable[str]:
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

        raw = buf.value.decode('utf-8')
        *lines, _ = raw.split('\r\n')
        return lines

    def search_device(self, broadcast_address: str, buffer_size: int) -> Iterable[str]:
        buf = ctypes.create_string_buffer(buffer_size)
        broadcast_address = broadcast_address.encode()
        protocol = b'UDP'  # Only UDP works, see SDK docs

        res = self.dll.SearchDevice(protocol, broadcast_address, buf)
        if res < 0:
            raise RuntimeError('SearchDevice failed, returned: {}'.format(str(res)))

        raw = buf.value.decode('utf-8')
        *lines, _ = raw.split("\r\n")
        return lines

    def __del__(self):
        self.disconnect()


class ZKAccess:
    """Main class to work with a device.
    Holds a connection and provides interface to PULL SDK functions
    """
    buffer_size = 4096

    def __init__(self,
                 connstr: Optional[bytes] = None,
                 device: Optional[ZKDevice] = None,
                 device_model: ZKModel = ZK400,
                 dllpath: str = 'plcommpro.dll',
                 log_capacity: Optional[int] = None):
        """
        :param connstr: Device connection string. If given then
         automatically connect to a device
        :param dllpath: Full path to plcommpro.dll
        :param device_model: Device model class. Default is C3-400
        """
        self.connstr = connstr
        self.device = device
        self.device_model = device_model
        self.sdk = ZKSDK(dllpath)
        self.event_log = EventLog(self.sdk, self.buffer_size, maxlen=log_capacity)

        if connstr is None and device is None:
            raise ValueError('Please specify either connstr or device')

        if device:
            if not connstr:
                self.connstr = \
                    'protocol=TCP,ipaddress={},port=4370,timeout=4000,passwd='.format(device.ip)
                self.connstr = self.connstr.encode()
            if not device_model:
                self.device_model = device.model

        if self.connstr:
            self.connect(self.connstr)

    @property
    def relays(self) -> 'RelayList':
        """Set of all relays"""
        mdl = self.device_model
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        return RelayList(sdk=self.sdk, relays=relays)

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
        self.sdk.control_device(ControlOperation.restart.value, 0, 0, 0, 0)

    @classmethod
    def search_devices(cls,
                       broadcast_address: str = '255.255.255.255',
                       dllpath: str = 'plcommpro.dll') -> Iterable[ZKDevice]:
        sdk = ZKSDK(dllpath)
        devices = sdk.search_device(broadcast_address, cls.buffer_size)
        return (ZKDevice(line) for line in devices)

    def __enter__(self):
        if not self.sdk.is_connected:
            self.connect(self.connstr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sdk.is_connected:
            self.disconnect()


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
            ControlOperation.output.value,
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
            self.sdk.control_device(ControlOperation.output.value,
                                    relay.number,
                                    relay.group.value,
                                    timeout,
                                    0)
    # FIXME: add __getitem__
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


class Event:
    """
    Represents one realtime event occured on the device
    Since the device returns event as string we need to parse it to the
    structured view. This class does this.
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

    def __str__(self):
        return 'Event(' \
               + ', '.join('{}={}'.format(k, getattr(self, k)) for k in self.__slots__) \
               + ')'

    def __repr__(self):
        return self.__str__()


class EventLog(deque):
    def __init__(self,
                 sdk: ZKSDK,
                 buffer_size: int,
                 maxlen: Optional[int] = None):
        super().__init__((), maxlen=maxlen)
        self.sdk = sdk
        self.buffer_size = buffer_size
        self.unread_index = 0

    @property
    def has_unread(self):
        return self.unread_index < len(self)

    @property
    def unread(self) -> Iterable[Event]:
        unread_index = self.unread_index
        self.unread_index = len(self)
        return self[unread_index:]

    def refresh(self) -> int:
        # ZKAccess always returns single event with code "255"
        # if no other events occured. So, skip it
        new_events = [e for e in self._pull_events() if e.event_type != '255']
        events_added = 0
        while new_events:
            events_added += len(new_events)
            old_len = len(self)
            self.extend(new_events)
            offset = (len(self) - old_len) - len(new_events)
            self.unread_index = max(self.unread_index + offset , 0)
            new_events = [e for e in self._pull_events() if e.event_type != '255']

        return min(len(self), events_added)

    def poll(self, timeout: int = 60) -> Optional[Iterable[Event]]:
        for _ in range(timeout):
            self.refresh()
            unread = list(self.unread)
            if unread:
                return unread
            time.sleep(1)

    def _pull_events(self) -> Iterable[Event]:
        events = self.sdk.get_rt_log(self.buffer_size)
        return (Event(s) for s in events)

    def __getitem__(self, item) -> Union[Iterable[Event], Event]:
        if not isinstance(item, slice):
            return super().__getitem__(item)

        seq = self
        start, stop, step = item.start, item.stop, item.step
        if step is not None and step < 0:
            seq = reversed(seq)
            step = -step
        if start is not None and start < 0:
            start = len(self) + start
        if stop is not None and stop < 0:
            stop = len(self) + stop
        return itertools.islice(seq, start, stop, step)

    def __str__(self):
        items_str = ', '.join(str(x) for x in self[:3])
        if len(self) > 6:
            items_str += ', ..., ' + ', '.join(str(x) for x in self[3:])
        return 'EventLog[{}]({})'.format(len(self), items_str)

    def __repr__(self):
        return self.__str__()
