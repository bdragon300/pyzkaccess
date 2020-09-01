import ctypes
from typing import Iterable, Optional

from .device import ZKModel, ZK400, ZKDevice
from .door import Door, DoorList
from .enum import ControlOperation
from .event import EventLog
from .reader import Reader, ReaderList
from .relay import Relay, RelayList
from .sdk import ZKSDK


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
        self._event_log = EventLog(self.sdk, self.buffer_size, maxlen=log_capacity)

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
    def readers(self) -> 'ReaderList':
        readers = [Reader(self.sdk, self._event_log, x) for x in self.device_model.readers_def]
        return ReaderList(sdk=self.sdk, event_log=self._event_log, readers=readers)

    @property
    def events(self) -> 'EventLog':
        return self._event_log

    @property
    def doors(self):
        mdl = self.device_model
        readers = [Reader(self.sdk, self._event_log, x) for x in self.device_model.readers_def]
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        door_relays = [
            RelayList(self.sdk, relays=[x for x in relays if x.number == door])
            for door in mdl.doors_def
        ]
        doors = [Door(self.sdk, self._event_log, door, relays, reader)
                 for door, relays, reader in zip(mdl.doors_def, door_relays, readers)]

        return DoorList(self.sdk, event_log=self._event_log, doors=doors)

    # TODO: aux inputs

    @property
    def dll_object(self) -> ctypes.WinDLL:
        """DLL object (`ctypes.WinDLL`). Read only."""
        return self.sdk.dll

    @property
    def handle(self) -> Optional[int]:
        """Device handle. `None` if there is no active connection.
        Read only.
        """
        return self.sdk.handle

    @classmethod
    def search_devices(cls,
                       broadcast_address: str = '255.255.255.255',
                       dllpath: str = 'plcommpro.dll') -> Iterable[ZKDevice]:
        sdk = ZKSDK(dllpath)
        devices = sdk.search_device(broadcast_address, cls.buffer_size)
        return (ZKDevice(line) for line in devices)

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

    def __enter__(self):
        if not self.sdk.is_connected:
            self.connect(self.connstr)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sdk.is_connected:
            self.disconnect()
