import ctypes
from datetime import datetime
from typing import Optional

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
        self._handle = None
        self._connstr = None
        self._device_model = device_model

        self._dll_object = ctypes.WinDLL(dllpath)

        if connstr:
            self.connect(connstr)

    @property
    def device_model(self) -> ZKModel:
        """Device model class. Read only"""
        return self._device_model

    @property
    def connstr(self) -> str:
        """Device connection string. Read only."""
        return self._connstr

    @property
    def dll_object(self) -> ctypes.WinDLL:
        """DLL object (`ctypes.WinDLL`). Read only."""
        return self._dll_object

    @property
    def handle(self):
        """Device handle. `None` if we are disconnected from a
        device. Read only.
        """
        return self._handle

    @property
    def relays(self) -> 'RelaySet':
        """Set of all relays"""
        return RelaySet(self)

    def __del__(self):
        if self._handle:
            self.disconnect()

    def __enter__(self):
        if not self._handle:
            self.connect(self.connstr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._handle:
            self.disconnect()

    def connect(self, connstr) -> None:
        """
        Connect to a device using connection string, ex:
        'protocol=TCP,ipaddress=192.168.22.201,port=4370,timeout=4000,passwd='
        :param connstr: device connection string
        :raises RuntimeError: if we are already connected
        :raises ConnectionError: connection attempt was failed
        :return:
        """
        if self._handle:
            raise RuntimeError('Already connected')

        self._connstr = connstr
        self._handle = self._dll_object.Connect(connstr)
        if self._handle == 0:
            self._handle = None
            raise ConnectionError("Unable to connect device using connstr '{}'".format(connstr))

    def disconnect(self) -> None:
        """Disconnect from a device"""
        if not self._handle:
            return

        self._dll_object.Disconnect(self._handle)
        self._handle = None

    def enable_relay(self, group: RelayGroup, number: int, timeout: int):
        """
        Enable a relay for the given time. If a relay is already
        enabled, its timeout will be refreshed
        :param group: Relay group to enable
        :param number: Relay number in group
        :param timeout: Timeout in seconds while relay will be enabled.
         Number between 0 and 255
        :raises ValueError: invalid parameter
        :raises RuntimeError: operation failed
        :return:
        """
        if number < 1 or number > self.device_model.relays:
            raise ValueError("Incorrect relay number: {}".format(number))
        if timeout < 0 or timeout > 255:
            raise ValueError("Incorrect timeout: {}".format(timeout))

        return self.zk_control_device(
            ControlOperation.output,
            number,
            group,
            timeout,
            0
        )

    def enable_relay_list(self, l, timeout):
        """
        Enable relays by mask for the given time. Receives list with
        desired relays state: non-zero means enabled, zero means
        disabled. This action overwrites previous relays state.

        E.g. [1, 0, 0, 0, 0, 0, 1, 0] means 1, 7 relays get turned
        on in order as they placed on the device. Other ones get
        turned off.
        :param l: list with relays states
        :param timeout: Seconds the relay will be enabled. Number between 0 and 255
        :raises RuntimeError: operation failed
        :return:
        """
        if timeout < 0 or timeout > 255:
            raise ValueError("Incorrect timeout: {}".format(timeout))
        if len(l) != self.device_model.relays:
            raise ValueError("Relay list length '{}' is not equal to relays count '{}'"
                             .format(len(l), self.device_model.relays))

        for i in range(self.device_model.relays):
            if l[i]:
                self.zk_control_device(
                    ControlOperation.output,
                    self.device_model.relays_def[i],
                    self.device_model.groups_def[i].value,
                    timeout,
                    0
                )

    def read_events(self, buffer_size=4096):
        """
        Read events from the device
        :param buffer_size:
        :return:
        """
        raw = self.zk_get_rt_log(buffer_size)
        *events_s, empty = raw.split('\r\n')

        return (ZKRealtimeEvent(s) for s in events_s)

    def zk_control_device(self, operation, p1, p2, p3, p4, options_str=''):
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
        res = self.dll_object.ControlDevice(
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

    def zk_get_rt_log(self, buffer_size):
        """
        Machinery method for retrieving events from device.
        :param buffer_size: Required. Buffer size in bytes that filled
         with contents
        :raises RuntimeError: if operation was failed
        :return: raw string with events
        """
        buf = ctypes.create_string_buffer(buffer_size)

        res = self.dll_object.GetRTLog(self.handle, buf, buffer_size)
        if res < 0:
            raise RuntimeError('GetRTLog failed, returned: {}'.format(str(res)))

        return buf.value.decode('utf-8')


class Relay:
    """Concrete relay"""
    def __init__(self, zk: ZKAccess, group: RelayGroup, number: int):
        self.zk = zk
        self.group = group
        self.number = number

    def enable(self, timeout: int) -> None:
        """
        Enable current relay
        :param timeout: Timeout in seconds while relay will be enabled.
         Number between 0 and 255
        :return:
        """
        self.zk.enable_relay(self.group, self.number, timeout)


class RelaySet:
    """Collection of relay objects which is used to perform group
    operations over multiple relays
    """
    def __init__(self, zk: ZKAccess, relays_mask: Optional[tuple] = None):
        """
        :param zk: ZKAccess object
        :param relays_mask: mask of active relays. Default is all active
        """
        self.zk = zk
        self.active_mask = relays_mask if relays_mask is not None else (1,) * zk.device_model.relays

    def enable(self, timeout: int) -> None:
        self.zk.enable_relay_list(self.active_mask, timeout)

    @property
    def aux(self) -> 'RelaySet':
        """Return set with active relays in aux group"""
        mask = tuple(int(self.zk.device_model.groups_def[i] == RelayGroup.aux)
                     for i in range(self.zk.device_model.relays))
        return self.__class__(self.zk, mask)

    @property
    def lock(self) -> 'RelaySet':
        """Return set with active relays in lock group"""
        mask = tuple(int(self.zk.device_model.groups_def[i] == RelayGroup.lock)
                     for i in range(self.zk.device_model.relays))
        return self.__class__(self.zk, mask)

    def __getitem__(self, item):
        mdl = self.zk.device_model
        # Apply slicing over active relays only (those ones which have
        # 1 in appropriate mask value)
        return [Relay(self.zk, g, n)
                for m, g, n in zip(self.active_mask, mdl.groups_def, mdl.relays_def)
                if m][item]

    def __len__(self):
        return sum(1 for x in self.active_mask if x)


#
# Device event
#
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
