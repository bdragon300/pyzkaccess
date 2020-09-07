__all__ = [
    'ZKAccess'
]
import pyzkaccess.ctypes as ctypes
from typing import Optional, Sequence

from .aux_input import AuxInput, AuxInputList
from .device import ZKModel, ZK400, ZKDevice
from .door import Door, DoorList
from .enum import ControlOperation
from .event import EventLog
from .param import DeviceParameters, DoorParameters
from .reader import Reader, ReaderList
from .relay import Relay, RelayList
import pyzkaccess.sdk


class ZKAccess:
    """Interface to a connected device"""

    #: Size in bytes of c-string buffer which is used to accept
    #: text data from PULL SDK functions
    buffer_size = 4096

    def __init__(self,
                 connstr: Optional[str] = None,
                 device: Optional[ZKDevice] = None,
                 device_model: type(ZKModel) = ZK400,
                 dllpath: str = 'plcommpro.dll',
                 log_capacity: Optional[int] = None):
        """
        :param connstr: Connection string. If given then
         we try to connect automatically to a device. Ex:
         'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        :param device: ZKDevice object to connect with. If
         given then we try to connect automatically to a device
        :param device_model: Device model. Default is C3-400
        :param dllpath: Full path to plcommpro.dll
        :param log_capacity: Mixumum capacity of events log. By default
         size is not limited
        :raises ZKSDKError: On connection error
        """
        self.connstr = connstr
        self.device_model = device_model
        self.sdk = pyzkaccess.sdk.ZKSDK(dllpath)
        self._device = device
        self._event_log = EventLog(self.sdk, self.buffer_size, maxlen=log_capacity)

        if device:
            if not connstr:
                self.connstr = \
                    'protocol=TCP,ipaddress={},port=4370,timeout=4000,passwd='.format(device.ip)
            if not device_model:
                self.device_model = device.model

        if self.connstr:
            self.connect(self.connstr)

    @property
    def doors(self):
        """Door object list, depends on device model.
        Door object incapsulates access to appropriate relays, reader,
        aux input, and also its events and parameters

        You can work with one object as with a slice. E.g. switch_on
        all relays of a door (`zk.doors[0].relays.switch_on(5)`) or
        of a slice (`zk.doors[:2].relays.switch_on(5)`)
        """
        mdl = self.device_model
        readers = (Reader(self.sdk, self._event_log, x) for x in mdl.readers_def)
        aux_inputs = (AuxInput(self.sdk, self._event_log, n) for n in mdl.aux_inputs_def)
        relays = (Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def))
        door_relays = (
            RelayList(self.sdk, relays=[x for x in relays if x.number == door])
            for door in mdl.doors_def
        )
        params = (DoorParameters(self.sdk, device_model=mdl, door_number=door)
                  for door in mdl.doors_def)

        seq = zip(mdl.doors_def, door_relays, readers, aux_inputs, params)
        doors = [Door(self.sdk, self._event_log, door, relays, reader, aux_input, params)
                 for door, relays, reader, aux_input, params in seq]

        return DoorList(self.sdk, event_log=self._event_log, doors=doors)

    @property
    def relays(self) -> 'RelayList':
        """Relay object list, depends on device model

        You can work with one object as with a slice. E.g. switch on
        a single relay (`zk.relays[0].switch_on(5)`) or a slice
        (`zk.relays[:2].switch_on(5)`)
        """
        mdl = self.device_model
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        return RelayList(sdk=self.sdk, relays=relays)

    @property
    def readers(self) -> 'ReaderList':
        """Reader object list, depends on device model

        You can work with one object as with a slice. E.g. get events
        of single reader (`zk.readers[0].events`) or a slice
        (`zk.readers[:2].events`)
        """
        readers = [Reader(self.sdk, self._event_log, x) for x in self.device_model.readers_def]
        return ReaderList(sdk=self.sdk, event_log=self._event_log, readers=readers)

    @property
    def aux_inputs(self):
        """Aux input object list, depends on device model

        You can work with one object as with a slice. E.g. get events
        of single input (`zk.aux_inputs[0].events`) or a slice
        (`zk.aux_inputs[:2].events`)
        """
        mdl = self.device_model
        aux_inputs = [AuxInput(self.sdk, self._event_log, n) for n in mdl.aux_inputs_def]
        return AuxInputList(self.sdk, event_log=self._event_log, aux_inputs=aux_inputs)

    @property
    def events(self) -> 'EventLog':
        """Device event log.

        This property returns all records pulled from a device.
        Keep in mind that log is not filled out automatically and
        should be refreshed periodically by hand using `refresh()`
        method. This is because working with ZKAccess has
        request-response nature and cannot up a tunnel which may be
        used to feed events.

        But you can use `poll()` method which awaits new events from
        a device and return them if any.

        Doors, inputs, readers have their own `events` property. Those
        properties just filters the same event log instance and
        return entries related to requested object.
        """
        return self._event_log

    @property
    def parameters(self):
        """Parameters related to the whole device such as datetime,
        connection settings and so forth. Door-specific parameters are
        accesible by `doors` property.
        """
        return DeviceParameters(self.sdk, self.device_model)

    @property
    def device(self) -> ZKDevice:
        """Current device object we connected with"""
        if self._device:
            return self._device

        if not self.sdk.is_connected:
            raise RuntimeError('Cannot create device while not connected')

        return ZKDevice(mac=None,
                        ip=self.parameters.ip_address,
                        serial_number=self.parameters.serial_number,
                        model=self.device_model,
                        version=None)

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
                       dllpath: str = 'plcommpro.dll') -> Sequence[ZKDevice]:
        """
        Classmethod which scans an Ethernet network with given
        broadcast address and returns all found ZK devices.

        Please keep in mind that process sends broadcast packets to
        perform a search which are not passed through routers. So you'll
        get results only for local network segment.

        The default broadcast address may not work in some cases, so
        it's better to specify your local network broadcast address.
        For example, if your ip is `192.168.22.123` and netmask is
        `255.255.255.0` or `/24` so address will be `192.168.22.255`.

        Returned objects can be used as `device=` parameter in
        constructor.
        :param broadcast_address: your local segment broadcast address
         as string. Default is '255.255.255.255'
        :param dllpath: path to a PULL SDK DLL. Default: 'plcommpro.dll'
        :return: iterable of found ZKDevice
        """
        sdk = pyzkaccess.sdk.ZKSDK(dllpath)
        devices = sdk.search_device(broadcast_address, cls.buffer_size)
        return tuple(ZKDevice(line) for line in devices)

    def connect(self, connstr: str) -> None:
        """
        Connect to a device using connection string, ex:
        'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        :param connstr: device connection string
        :return:
        """
        if self.sdk.is_connected:
            if connstr != self.connstr:
                raise ValueError('Please disconnect before connecting with other connstr')
            return

        self.connstr = connstr
        self.sdk.connect(connstr)

    def disconnect(self) -> None:
        """Disconnect from a device"""
        self.sdk.disconnect()

    def restart(self) -> None:
        """Restart a device"""
        self.sdk.control_device(ControlOperation.restart.value, 0, 0, 0, 0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sdk.is_connected:
            self.disconnect()
