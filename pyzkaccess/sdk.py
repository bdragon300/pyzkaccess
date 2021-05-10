__all__ = [
    'ZKSDK'
]
from typing import Sequence, Mapping, Any, Generator, Optional

import pyzkaccess.ctypes_ as ctypes
from .exceptions import ZKSDKError


class ZKSDK:
    """This is machinery class which directly calls SDK functions.
    This is a wrapper around DLL functions of SDK, it incapsulates
    working with ctypes, handles errors and holds connection info.
    """
    def __init__(self, dllpath: str):
        """
        Args:
            dllpath (str): path to a DLL file. E.g. "plcommpro.dll"

        """
        self.handle = None
        self.dll = ctypes.WinDLL(dllpath)

    @property
    def is_connected(self) -> bool:
        """Return True if connection is active"""
        return bool(self.handle is not None)

    def connect(self, connstr: str) -> None:
        """Connect to a device.

        SDK: Connect()

        Args:
            connstr (str): connection string, see docs

        Returns:
            None

        Raises:
            ZKSDKError: return:

        """
        connstr = connstr.encode()
        self.handle = self.dll.Connect(connstr)
        if self.handle == 0:
            self.handle = None
            err = self.dll.PullLastError()
            raise ZKSDKError("Unable to connect a device using connstr {}".format(connstr), err)

    def disconnect(self) -> None:
        """Disconnect from a device

        SDK: Disconnect()

        Returns:
            None
        """
        if not self.handle:
            return

        self.dll.Disconnect(self.handle)
        self.handle = None

    def control_device(self, operation, p1, p2, p3, p4, options_str='') -> int:
        """Perform an action on a device such as relay switching or reboot.
        For parameter meaning please see SDK docs.

        SDK: ControlDevice()

        Args:
            operation (int): operation id
            p1 (int): Number, depends on operation id
            p2 (int): Number, depends on operation id
            p3 (int): Number, depends on operation id
            p4 (int): Number, depends on operation id
            options_str (str, optional): String, depends on
                operation id

        Returns:
            int: DLL function result code, 0 or positive number

        Raises:
            ZKSDKError: on SDK error

        """
        err = self.dll.ControlDevice(
            self.handle,
            operation,
            p1,
            p2,
            p3,
            p4,
            options_str
        )
        if err < 0:
            raise ZKSDKError('ControlDevice failed for operation {}'.format(operation), err)

        return err

    def get_rt_log(self, buffer_size: int) -> Sequence[str]:
        """Retrieve unread realtime events from a device

        SDK: GetRTLog()

        Args:
            buffer_size (int): size in bytes of buffer which is filled
                with contents

        Returns:
            Sequence[str]: event string lines

        Raises:
            ZKSDKError: on SDK error

        """
        buf = ctypes.create_string_buffer(buffer_size)

        err = self.dll.GetRTLog(self.handle, buf, buffer_size)
        if err < 0:
            raise ZKSDKError('GetRTLog failed', err)

        raw = buf.value.decode('utf-8')
        if raw == '\r\n':
            return []

        *lines, _ = raw.split('\r\n')
        return lines

    def search_device(self, broadcast_address: str, buffer_size: int) -> Sequence[str]:
        """Perform network scan in order to collect available ZK devices

        SDK: SearchDevice()

        Args:
            broadcast_address (str): network broadcast address
            buffer_size (int): size in bytes of buffer which is filled
                with contents

        Returns:
            Sequence[str]: device string lines

        Raises:
            ZKSDKError: on SDK error

        """
        buf = ctypes.create_string_buffer(buffer_size)
        broadcast_address = broadcast_address.encode()
        protocol = b'UDP'  # Only UDP works, see SDK docs

        err = self.dll.SearchDevice(protocol, broadcast_address, buf)
        if err < 0:
            raise ZKSDKError('SearchDevice failed', err)

        raw = buf.value.decode('utf-8')
        if raw == '\r\n':
            return []
        *lines, _ = raw.split("\r\n")
        return lines

    def get_device_param(self, parameters: Sequence[str], buffer_size: int) -> Mapping[str, str]:
        """Fetch given device parameters

        SDK: GetDeviceParam()

        Args:
            parameters (Sequence[str]): sequence with parameter names
                to be requested
            buffer_size (int): size in bytes of buffer which is filled
                with contents

        Returns:
             Mapping[str, str]: dict with requested parameters value.
                Each value is string

        Raises:
            ZKSDKError: on SDK error

        """
        buf = ctypes.create_string_buffer(buffer_size)
        results = {}

        # Device can return maximum 30 parameters for one call. See SDK
        #  docs. So fetch them in loop by bunches of 30 items
        parameters_copy = list(parameters)
        while parameters_copy:
            query_params = parameters_copy[:30]
            query = ','.join(query_params).encode()
            del parameters_copy[:30]

            err = self.dll.GetDeviceParam(self.handle, buf, buffer_size, query)
            if err < 0:
                raise ZKSDKError('GetDeviceParam failed', err)

            for pair in buf.value.decode().split(','):
                key, val = pair.split('=')
                results[key] = val

        if results.keys() != set(parameters):
            raise ValueError(
                'Parameters returned by a device are differ than parameters was requested'
            )
        return results

    def set_device_param(self, parameters: Mapping[str, Any]) -> None:
        """Set given device parameters

        SDK: SetDeviceParam()

        Args:
            parameters (Mapping[str, Any]): dict with parameter
                names and values to be set. Every value will be
                casted to string

        Returns:
            None

        Raises:
            ZKSDKError: on SDK error

        """
        if not parameters:
            return

        # Device can accept maximum 20 parameters for one call. See SDK
        #  docs. So send them in loop by bunches of 20 items
        keys = list(sorted(parameters.keys()))
        while keys:
            query_keys = keys[:20]
            query = ','.join('{}={}'.format(k, parameters[k]) for k in query_keys).encode()
            del keys[:20]

            err = self.dll.SetDeviceParam(self.handle, query)
            if err < 0:
                raise ZKSDKError('SetDeviceParam failed', err)

    def get_device_data(
            self,
            table_name: str,
            fields: Sequence[str],
            filters: Mapping[str, str],
            buffer_size: int,
            new_records_only: bool = False) -> Generator[Mapping[str, str], None, None]:
        """Retrieve records from a given data table

        SDK: GetDeviceData()

        Args:
            table_name (str): name of table to retrieve records from
            fields (Sequence[str]): list of fields to query.
                Empty sequence is treated as "all fields"
            filters (Mapping[str, str]): query conditions to apply
            buffer_size (int): size in bytes of buffer which is filled
                with contents
            new_records_only (bool, default=False): true means to
                consider only unread records in table, otherwise
                all records will be considered

        Yields:
            Mapping[str, str]: ordered dicts with table records

        Raises:
            ZKSDKError: on SDK error

        """
        buf = ctypes.create_string_buffer(buffer_size)

        query_table = table_name.encode()
        query_fields = '\t'.join(fields).encode() if fields else b'*'
        query_conditions = '\t'.join('{}={}'.format(k, v) for k, v in filters.items()).encode()
        query_options = ('NewRecord' if new_records_only else '').encode()

        err = self.dll.GetDeviceData(self.handle, buf, buffer_size, query_table,
                                     query_fields, query_conditions, query_options)
        if err < 0:
            raise ZKSDKError('GetDeviceData failed', err)

        raw = buf.value.decode('utf-8')

        *lines, _ = raw.split('\r\n')
        headers = lines.pop(0).split(',')
        for line in lines:
            cols = line.split(',')
            yield {k: v for k, v in zip(headers, cols) if not fields or k in fields}

    def set_device_data(
            self, table_name: str
    ) -> Generator[None, Optional[Mapping[str, str]], None]:
        """Insert records to a given data table. Records are received
        through a generator.

        Example::

            g = sdk.set_device_data('user')
            g.send(None)  # Initialize generator
            for rec in records:
                g.send(rec)
            g.send(None)   # Invoke sdk call

        SDK: SetDeviceData()

        Args:
            table_name (str): name of table to write data to

        Yields:
            Optional[Mapping[str, str]]: generator that
                accepts mappings with records via `.send()` method.
                `.send(None)` commits writing

        Raises:
            ZKSDKError: on SDK error

        """
        query_table = table_name.encode()
        query_records = []
        record = yield
        while record is not None:
            query_records.append(
                '\t'.join('{}={}'.format(k, v) for k, v in record.items() if v is not None)
            )
            record = yield

        if not query_records:
            return

        query_records = '\r\n'.join(query_records).encode()
        query_records += b'\r\n'

        # `Options` parameter should be null according to SDK docs
        err = self.dll.SetDeviceData(self.handle, query_table, query_records, '')
        if err < 0:
            raise ZKSDKError('SetDeviceData failed', err)

    def get_device_data_count(self, table_name: str) -> int:
        """Return records count in a given data table

        SDK: GetDeviceDataCount()

        Args:
            table_name (str): name of table to get records count from

        Returns:
            int: count of records in table

        Raises:
            ZKSDKError: on SDK error

        """
        query_table = table_name.encode()

        # `Filter` and `Options` parameters should be null according to SDK docs
        err = self.dll.GetDeviceDataCount(self.handle, query_table, '', '')
        if err < 0:
            raise ZKSDKError('GetDeviceDataCount failed', err)
        return err

    def delete_device_data(
            self, table_name: str
    ) -> Generator[None, Optional[Mapping[str, str]], None]:
        """Delete given records from a data table. Records are received
        through a generator.

        Example::

            g = sdk.delete_device_data('user')
            g.send(None)  # Initialize generator
            for rec in records:
                g.send(rec)
            g.send(None)   # Invoke sdk call

        SDK: DeleteDeviceData()

        Args:
            table_name (str): name of table to delete data from

        Yields:
            Optional[Mapping[str, str]]: generator that
                accepts mappings with records via `.send()` method.
                `.send(None)` commits deleting

        Raises:
            ZKSDKError: on SDK error

        """
        query_table = table_name.encode()
        query_records = []
        record = yield
        while record is not None:
            query_records.append(
                '\t'.join('{}={}'.format(k, v) for k, v in record.items() if v is not None)
            )
            record = yield

        if not query_records:
            return

        query_records = '\r\n'.join(query_records).encode()
        query_records += b'\r\n'

        # `Options` parameter should be null according to SDK docs
        err = self.dll.DeleteDeviceData(self.handle, query_table, query_records, '')
        if err < 0:
            raise ZKSDKError('DeleteDeviceData failed', err)

    def __del__(self):
        self.disconnect()
