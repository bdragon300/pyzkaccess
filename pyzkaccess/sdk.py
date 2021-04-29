__all__ = [
    'ZKSDK'
]
from typing import Sequence, Mapping, Any, Generator, Optional

import pyzkaccess.ctypes as ctypes
from .exceptions import ZKSDKError


class ZKSDK:
    """This is machinery class which directly calls SDK functions.
    This is a wrapper around DLL functions of SDK, it incapsulates
    working with ctypes, handles errors and holds connection info.
    """
    def __init__(self, dllpath: str):
        """
        :param dllpath: path to a DLL file. Typically "plcommpro.dll"
        """
        self.handle = None
        self.dll = ctypes.WinDLL(dllpath)

    @property
    def is_connected(self) -> bool:
        """Return True if connection is active"""
        return bool(self.handle is not None)

    def connect(self, connstr: str) -> None:
        """
        Connect to a device.

        SDK: Connect()
        :param connstr: connection string, see docs
        :raises ZKSDKError:
        :return:
        """
        connstr = connstr.encode()
        self.handle = self.dll.Connect(connstr)
        if self.handle == 0:
            self.handle = None
            err = self.dll.PullLastError()
            raise ZKSDKError("Unable to connect a device using connstr {}".format(connstr), err)

    def disconnect(self) -> None:
        """
        Disconnect from a device

        SDK: Disconnect()
        :return:
        """
        if not self.handle:
            return

        self.dll.Disconnect(self.handle)
        self.handle = None

    def control_device(self, operation, p1, p2, p3, p4, options_str='') -> int:
        """
        Perform an action on a device such as relay switching or reboot.
        For parameter meaning please see SDK docs.

        SDK: ControlDevice()
        :param operation: Number, operation id
        :param p1: Number, depends on operation id
        :param p2: Number, depends on operation id
        :param p3: Number, depends on operation id
        :param p4: Number, depends on operation id
        :param options_str: String, depends on operation id
        :raises ZKSDKError:
        :return: DLL function result code, 0 or positive number
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
        """
        Retrieve unread realtime events from a device

        SDK: GetRTLog()
        :param buffer_size: size in bytes of buffer which is filled
         with contents
        :raises ZKSDKError:
        :return: event string lines
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
        """
        Perform network scan in order to collect available ZK devices

        SDK: SearchDevice()
        :param broadcast_address: network broadcast address
        :param buffer_size: size in bytes of buffer which is filled
         with contents
        :raises ZKSDKError:
        :return: device string lines
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
        """
        Fetch given device parameters

        SDK: GetDeviceParam()
        :param parameters: sequence with parameter names to be requested
        :param buffer_size: size in bytes of buffer which is filled
         with contents
        :raises ZKSDKError:
        :return: dict with requested parameters value. Each value is
         string
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
        """
        Set given device parameters

        SDK: SetDeviceParam()
        :param parameters: dict with parameter names and values to be
         set. Every value will be casted to string
        :raises ZKSDKError:
        :return:
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
        """
        Retrieve records from a given data table

        SDK: GetDeviceData()
        :param table_name: name of table to retrieve records from
        :param fields: list of fields to query. Empty sequence is
         treated as "all fields"
        :param filters: query conditions to apply
        :param buffer_size: size in bytes of buffer which is filled
         with contents
        :param new_records_only: true means to consider only unread
         records in table, otherwise all records will be considered
        :return: ordered dicts with table records
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
        """
        Insert records to a given data table. Records are received
        through a generator.

        Example::

            g = sdk.set_device_data('user')
            g.send(None)  # Initialize generator
            for rec in records:
                g.send(rec)
            g.send(None)   # Invoke sdk call

        SDK: SetDeviceData()
        :param table_name: name of table to write data to
        :return:
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
        """
        Return records count in a given data table

        SDK: GetDeviceDataCount()
        :param table_name: name of table to get records count from
        :return: count of records
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
        """
        Delete given records from a data table. Records are received
        through a generator.

        Example::

            g = sdk.delete_device_data('user')
            g.send(None)  # Initialize generator
            for rec in records:
                g.send(rec)
            g.send(None)   # Invoke sdk call

        SDK: DeleteDeviceData()

        :param table_name: name of table to delete data from
        :return:
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
