__all__ = [
    'ZKAccess'
]

import io
import os
import sys
from typing import Optional, Sequence, Union, Type, BinaryIO

import pyzkaccess.ctypes_ as ctypes
import pyzkaccess.sdk
from pyzkaccess.exceptions import ZKSDKError
from .aux_input import AuxInput, AuxInputList
from .device import ZKModel, ZK400, ZKDevice
from .device_data.queryset import QuerySet
from .device_data.model import Model, models_registry
from .door import Door, DoorList
from .enums import ControlOperation, ChangeIPProtocol
from .event import EventLog
from .param import DeviceParameters, DoorParameters
from .reader import Reader, ReaderList
from .relay import Relay, RelayList


class ZKAccess:
    """Interface to a connected ZKAccess device"""

    buffer_size = 4096
    """Size in bytes of c-string buffer which is used to accept
    text data from PULL SDK functions
    """

    query_buffer_size = None
    """Size in bytes of c-string buffer for result of query to
    data tables. If None then size will be guessed automatically
    """

    queryset_class = QuerySet

    def __init__(self,
                 connstr: Optional[str] = None,
                 device: Optional[ZKDevice] = None,
                 device_model: Type[ZKModel] = ZK400,
                 dllpath: str = 'plcommpro.dll',
                 log_capacity: Optional[int] = None):
        """
        Args:
            connstr (str, optional): Connection string. If given then
                we try to connect automatically to a device. Ex:
                'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
            device (ZKDevice, optional): ZKDevice object to connect to.
                If given then we try to connect automatically to a
                device
            device_model (Type[ZKModel], default=ZK400): Device model.
            dllpath (str, default=plcommpro.dll): Full path to
                plcommpro.dll
            log_capacity (int, optional): Mixumum capacity of events
                log. By default size is not limited

        Raises:
          ZKSDKError: On connection error

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
            if not device_model:  # FIXME: if device_model and device.model are in conflict
                self.device_model = device.model

        if self.connstr:
            self.connect(self.connstr)

    def table(self, table: Union[Type[Model], str]) -> QuerySet:
        """Return a QuerySet object for a given table

        Args:
            table (Union[Type[Model], str]): data table name or Model
                object/class

        Returns:
            QuerySet: new empty QuerySet object binded with a given
                table

        """
        table = self._get_table(table)
        return self.queryset_class(self.sdk, table, self.query_buffer_size)

    def upload_file(self, remote_filename: str, data: BinaryIO) -> None:
        """Upload a file with given name to a device

        Args:
            remote_filename (str): filename to upload
            data (BinaryIO): file data binary stream
        """
        pos = data.tell()
        data.seek(0, os.SEEK_END)
        size = data.tell() - pos
        data.seek(pos)

        self.sdk.set_device_file_data(remote_filename, data.read(), size)

        data.seek(pos)

    def download_file(self, remote_filename: str, buffer_size: Optional[int] = None) -> BinaryIO:
        """Download file with given name from a device.

        Args:
            remote_filename (str): filename to download from a device
            buffer_size (int, optional): size of buffer for downloading
                file data. If omitted, then it will be guessed
                automatically

        Returns:
            BinaryIO: file data binary stream
        """
        estimated_size = buffer_size
        if buffer_size is None:
            estimated_size = 1 * 1024 * 1024  # Start from 4kb

        data = self.sdk.get_device_file_data(remote_filename, estimated_size)
        while buffer_size is None and len(data) >= estimated_size:
            # Read data size == buffer_size means in most cases
            # that buffer got overflowed and it's needed to
            # increase buffer size and read again
            estimated_size *= 2
            data = self.sdk.get_device_file_data(remote_filename, estimated_size)

        res = io.BytesIO(data)
        res.seek(0)
        return res

    def cancel_alarm(self):
        """Move a device from alarm state to a normal state"""
        self.sdk.control_device(ControlOperation.cancel_alarm.value, 0, 0, 0, 0)

    @property
    def doors(self) -> DoorList:
        """Door object list, depends on device model.
        Door object incapsulates access to appropriate relays, reader,
        aux input, and also its events and parameters

        You can work with one object as with a slice. E.g. switch_on
        all relays of a door::

            zk.doors[0].relays.switch_on(5)

        or a slice::

            zk.doors[:2].relays.switch_on(5)

        Returns:
            DoorList: list of all doors
        """
        mdl = self.device_model
        readers = (Reader(self.sdk, self._event_log, x) for x in mdl.readers_def)
        aux_inputs = (AuxInput(self.sdk, self._event_log, n) for n in mdl.aux_inputs_def)
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
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
    def relays(self) -> RelayList:
        """Relay object list, depends on device model

        You can work with one object as with a slice. E.g. switch on
        a single relay::

            zk.relays[0].switch_on(5)

        or a slice::

            zk.relays[:2].switch_on(5)

        Returns:
            RelayList: list of all relays
        """
        mdl = self.device_model
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        return RelayList(sdk=self.sdk, relays=relays)

    @property
    def readers(self) -> ReaderList:
        """Reader object list, depends on device model

        You can work with one object as with a slice. E.g. get events
        of single reader::

            zk.readers[0].events

        or a slice::

            zk.readers[:2].events

        Returns:
            ReaderList: list of all readers
        """
        readers = [Reader(self.sdk, self._event_log, x) for x in self.device_model.readers_def]
        return ReaderList(sdk=self.sdk, event_log=self._event_log, readers=readers)

    @property
    def aux_inputs(self) -> AuxInputList:
        """Aux input object list, depends on device model

        You can work with one object as with a slice. E.g. get events
        of single input::

            zk.aux_inputs[0].events

        or a slice::

            zk.aux_inputs[:2].events

        Returns:
            AuxInputList: list of all aux inputs
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

        Returns:
            EventLog: unfiltered event log object
        """
        return self._event_log

    @property
    def parameters(self) -> DeviceParameters:
        """Parameters related to the whole device such as datetime,
        connection settings and so forth. Door-specific parameters are
        accesible by `doors` property.

        Returns:
            DeviceParameters: parameters object
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
        """Classmethod which scans an Ethernet network with given
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

        Args:
            broadcast_address (str, default=255.255.255.255): your
                local segment broadcast address as string
            dllpath (str, default=plcommpro.dll): path to a PULL
                SDK DLL

        Returns:
            Sequence[ZKDevice]: iterable with found devices

        """
        sdk = pyzkaccess.sdk.ZKSDK(dllpath)
        try:
            devices = sdk.search_device(broadcast_address, cls.buffer_size)
        except ZKSDKError as e:
            # If no devices found, the -2 error is raised by SDK
            # Return just empty list in this case
            if e.err == -2:
                return ()
            raise

        return tuple(ZKDevice(line) for line in devices)

    @classmethod
    def change_ip(cls,
                  mac_address: str,
                  new_ip_address: str,
                  broadcast_address: str = '255.255.255.255',
                  protocol: ChangeIPProtocol = ChangeIPProtocol.udp,
                  dllpath: str = 'plcommpro.dll'
    ) -> None:
        """
        Classmethod that changes IP address on a device by sending
        broadcast packets to the given broadcast address. For security
        reasons, network settings can only be changed on devices with
        no password.

        The default broadcast address may not work in some cases, so
        it's better to specify your local network broadcast address.
        For example, if your ip is `192.168.22.123` and netmask is
        `255.255.255.0` or `/24` so address will be `192.168.22.255`.

        Args:
            mac_address (str): MAC address of a device
            new_ip_address (str): new IP address to be set on a device
            broadcast_address (str, default=255.255.255.255): broadcast
                network address
            protocol (ChangeIPProtocol, default=ChangeIPProtocol.udp): a
                protocol to use for sending broadcast packets
            dllpath (str, default=plcommpro.dll): path to a PULL
                SDK DLL

        Returns:
            bool: True if operation was successful
        """
        sdk = pyzkaccess.sdk.ZKSDK(dllpath)
        sdk.modify_ip_address(mac_address, new_ip_address, broadcast_address, protocol.value)

    def connect(self, connstr: str) -> None:
        """Connect to a device using connection string, ex:
        'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='

        Args:
            connstr (str): device connection string

        Returns:
            None
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

    @staticmethod
    def _get_table(table) -> Type[Model]:
        if isinstance(table, str):
            table = models_registry[table]
        elif isinstance(table, Model):
            table = table.__class__
        elif not (isinstance(table, type) and issubclass(table, Model)):
            raise TypeError('Table must be either a data table object/class or a table name')

        return table

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sdk.is_connected:
            self.disconnect()
