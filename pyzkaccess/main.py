__all__ = ["ZKAccess"]

import io
import os
from typing import Any, BinaryIO, ClassVar, Optional, Tuple, Type, TypeVar, Union

import pyzkaccess.ctypes_ as ctypes
import pyzkaccess.sdk
from pyzkaccess.aux_input import AuxInput, AuxInputList
from pyzkaccess.device import ZK400, ZKDevice, ZKModel
from pyzkaccess.device_data.model import Model, models_registry
from pyzkaccess.device_data.queryset import QuerySet
from pyzkaccess.door import Door, DoorList
from pyzkaccess.enums import ChangeIPProtocol, ControlOperation
from pyzkaccess.event import EventLog
from pyzkaccess.exceptions import ZKSDKError
from pyzkaccess.param import DeviceParameters, DoorParameters
from pyzkaccess.reader import Reader, ReaderList
from pyzkaccess.relay import Relay, RelayList

_ZKAccessT = TypeVar("_ZKAccessT", bound="ZKAccess")


class ZKAccess:
    """ZKAccess device, the main class to work with ZKAccess devices.

    Makes connection to a device, provides access to its data tables,
    doors, readers, relays, aux inputs, and events."""

    buffer_size: ClassVar[int] = 4096
    """Size in bytes of underlying buffer for text results of PULL SDK functions"""

    query_buffer_size: ClassVar[Optional[int]] = None
    """Size in bytes of underlying buffer for data table query results.
    If None then the size will be guessed automatically.
    """

    queryset_class: ClassVar[Type[QuerySet]] = QuerySet

    def __init__(
        self,
        connstr: Optional[str] = None,
        device: Optional[ZKDevice] = None,
        device_model: Type[ZKModel] = ZK400,
        dllpath: str = "plcommpro.dll",
        log_capacity: Optional[int] = None,
    ):
        """ZKAccess constructor

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
                self.connstr = f"protocol=TCP,ipaddress={device.ip},port=4370,timeout=4000,passwd="
            if not device_model:
                self.device_model = device.model

        if self.connstr:
            self.connect(self.connstr)

    def table(self, table: Union[Type[Model], str]) -> QuerySet:
        """Return a QuerySet object for a given table

        Args:
            table (Union[Type[Model], str]): data table name or Model
                object/class

        Returns:
            QuerySet: new empty QuerySet object

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
        estimated_size = 1 * 1024 * 1024  # Start from 4kb
        if buffer_size is not None:
            estimated_size = buffer_size

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

    def cancel_alarm(self) -> None:
        """Switch a device from the alarm mode to the normal mode"""
        self.sdk.control_device(ControlOperation.cancel_alarm.value, 0, 0, 0, 0)

    @property
    def doors(self) -> DoorList:
        """Door object list of all doors available on a device.

        DoorList object can make a group operations on relays, reader,
        aux input, events and parameters.

        By default all doors are returned (switch on *all* relays of *all* doors)::

            zk.doors.relays.switch_on(5)

        You can limit the list only to a particular door (the same for door #0)::

            zk.doors[0].relays.switch_on(5)

        Or you can limit it to the range of doors (the same for doors 0, 1)::

            zk.doors[:2].relays.switch_on(5)

        Returns:
            DoorList: door list with all doors accessible
        """
        mdl = self.device_model
        readers = (Reader(self.sdk, self._event_log, x) for x in mdl.readers_def)
        aux_inputs = (AuxInput(self.sdk, self._event_log, n) for n in mdl.aux_inputs_def)
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        door_relays = (RelayList(self.sdk, relays=[x for x in relays if x.number == door]) for door in mdl.doors_def)
        params = (DoorParameters(self.sdk, device_model=mdl, door_number=door) for door in mdl.doors_def)

        seq = zip(mdl.doors_def, door_relays, readers, aux_inputs, params)
        doors = [
            Door(self.sdk, self._event_log, door, relays, reader, aux_input, params)
            for door, relays, reader, aux_input, params in seq
        ]

        return DoorList(self.sdk, event_log=self._event_log, doors=doors)

    @property
    def relays(self) -> RelayList:
        """Relays object list of all relays available on a device.

        By default all relays are returned (switch on *all* relays)::

            zk.relays.switch_on(5)

        You can limit the list only to a particular relay (switch on #0)::

            zk.relays[0].switch_on(5)

        Or you can limit it to the range of relays (switch #0, #1)::

            zk.relays[:2].switch_on(5)

        Returns:
            RelayList: relay list with all relays accessible
        """
        mdl = self.device_model
        relays = [Relay(self.sdk, g, n) for g, n in zip(mdl.groups_def, mdl.relays_def)]
        return RelayList(sdk=self.sdk, relays=relays)

    @property
    def readers(self) -> ReaderList:
        """Readers object list of all readers available on a device.

        By default all readers are returned (get events from *all* readers)::

            zk.relays.events

        You can limit the list only to a particular reader (get events from #0)::

            zk.readers[0].events

        Or you can limit it to the range of readers (get events from #0, #1)::

            zk.readers[:2].events

        Returns:
            ReaderList: reader list with all readers accessible
        """
        readers = [Reader(self.sdk, self._event_log, x) for x in self.device_model.readers_def]
        return ReaderList(sdk=self.sdk, event_log=self._event_log, readers=readers)

    @property
    def aux_inputs(self) -> AuxInputList:
        """Auxiliary inputs list of all aux inputs available on a device.

        By default all aux inputs are returned (get events from *all* inputs)::

            zk.aux_inputs.events

        You can limit the list only to a particular aux input (get events from #0)::

            zk.aux_inputs[0].events

        Or you can limit it to the range of aux inputs (get events from #0, #1)::

            zk.aux_inputs[:2].events

        Returns:
            AuxInputList: aux inputs list with all aux inputs accessible
        """
        mdl = self.device_model
        aux_inputs = [AuxInput(self.sdk, self._event_log, n) for n in mdl.aux_inputs_def]
        return AuxInputList(self.sdk, event_log=self._event_log, aux_inputs=aux_inputs)

    @property
    def events(self) -> "EventLog":
        """Device event log.

        The `EventLog` object acts just as a container of events
        with additional methods. To keep the event log up to date,
        you should make manual method calls -- see `EventLog` class
        description for more details.

        Returns:
            EventLog: event log object
        """
        return self._event_log

    @property
    def parameters(self) -> DeviceParameters:
        """Parameters that are applied to the entire device, such as
        datetime, connection settings and so forth. The door-specific
        parameters are accesible by `doors` property.

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
            raise RuntimeError("Cannot create device while not connected")

        return ZKDevice(
            mac=None,
            ip=self.parameters.ip_address,
            serial_number=self.parameters.serial_number,
            model=self.device_model,
            version=None,
        )

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
    def search_devices(
        cls, broadcast_address: str = "255.255.255.255", dllpath: str = "plcommpro.dll"
    ) -> Tuple[ZKDevice, ...]:
        """Classmethod that scans the local network for active C3
        devices and returns a list of found devices.

        This process sends broadcast packets to the local network
        segment and waits for responses. Generally, the broadcast
        packets can't pass through routers (however, it depends on
        network configuration), so you'll get results only for local
        network segment.

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
            Tuple[ZKDevice, ...]: tuple with found devices

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
    def change_ip(  # pylint: disable=missing-param-doc
        cls,
        mac_address: str,
        new_ip_address: str,
        broadcast_address: str = "255.255.255.255",
        protocol: ChangeIPProtocol = ChangeIPProtocol.udp,
        dllpath: str = "plcommpro.dll",
    ) -> None:
        """Classmethod that resets the device IP address by its MAC address.
        For that it sends the broadcast packets to the given broadcast address.
        For security reasons, the IP address can only be reset on devices
        with no password.

        This function supports two modes: UDP and Ethernet.

        The UDP mode is the default one. It sends UDP broadcast packets to the
        given broadcast address. Typically, such packets doesn't pass through
        routers (however, it depends on network configuration), so you'll get
        results only for the local network segment.

        The Ethernet mode sends Ethernet broadcast frames with broadcast MAC
        address. Usually the Ethernet frames can not pass neither through routers
        nor through other network hardware, such as switches. Basically, this
        mode is useful only if you directly connected a device to your
        computer's Ethernet port.

        The default broadcast address may not work in some cases, so
        it's better to specify your local network broadcast address.
        For example, if your ip is `192.168.22.123` and netmask is
        `255.255.255.0` or `/24` so address will be `192.168.22.255`.

        Args:
            mac_address (str): device MAC address
            new_ip_address (str): new IP address to be set on a device
            broadcast_address (str, default=255.255.255.255): broadcast
                network address
            protocol (ChangeIPProtocol, default=ChangeIPProtocol.udp): a
                protocol to use for sending broadcast packets
            dllpath (str, default="plcommpro.dll"): path to a PULL
                SDK DLL
        """
        sdk = pyzkaccess.sdk.ZKSDK(dllpath)
        sdk.modify_ip_address(mac_address, new_ip_address, broadcast_address, protocol.value)

    def connect(self, connstr: str) -> None:
        """Connect to a device using a connection string, ex:
        'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='

        Args:
            connstr (str): device connection string
        """
        if self.sdk.is_connected:
            if connstr != self.connstr:
                raise ValueError("Please disconnect before connecting with other connstr")
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
    def _get_table(table: Union[str, Model, Type[Model]]) -> Type[Model]:
        if isinstance(table, str):
            table = models_registry[table]
        elif isinstance(table, Model):
            table = table.__class__
        elif not (isinstance(table, type) and issubclass(table, Model)):
            raise TypeError("Table must be either a data table object/class or a table name")

        return table

    def __enter__(self: _ZKAccessT) -> _ZKAccessT:
        return self

    def __exit__(self, *_: Any) -> None:
        if self.sdk.is_connected:
            self.disconnect()
