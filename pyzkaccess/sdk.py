import ctypes
from typing import Sequence, Mapping, Any

from .exceptions import ZKSDKError


class ZKSDK:
    def __init__(self, dllpath: str):
        self.dll = ctypes.WinDLL(dllpath)
        self.handle = None

    @property
    def is_connected(self) -> bool:
        return bool(self.handle is not None)

    def connect(self, connstr: str) -> None:
        connstr = connstr.encode()
        self.handle = self.dll.Connect(connstr)
        if self.handle == 0:
            self.handle = None
            err = self.dll.PullLastError()
            raise ZKSDKError("Unable to connect a device using connstr {}".format(connstr), err)

    def disconnect(self) -> None:
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
        Machinery method for retrieving events from device.
        :param buffer_size: Required. Buffer size in bytes that filled
         with contents
        :raises RuntimeError: if operation was failed
        :return: raw string with events
        """
        buf = ctypes.create_string_buffer(buffer_size)

        err = self.dll.GetRTLog(self.handle, buf, buffer_size)
        if err < 0:
            raise ZKSDKError('GetRTLog failed', err)

        raw = buf.value.decode('utf-8')
        *lines, _ = raw.split('\r\n')
        return lines

    def search_device(self, broadcast_address: str, buffer_size: int) -> Sequence[str]:
        buf = ctypes.create_string_buffer(buffer_size)
        broadcast_address = broadcast_address.encode()
        protocol = b'UDP'  # Only UDP works, see SDK docs

        err = self.dll.SearchDevice(protocol, broadcast_address, buf)
        if err < 0:
            raise ZKSDKError('SearchDevice failed', err)

        raw = buf.value.decode('utf-8')
        *lines, _ = raw.split("\r\n")
        return lines

    def get_device_param(self, parameters: Sequence[str], buffer_size: int) -> Mapping[str, str]:
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
        if not parameters:
            return

        # Device can accept maximum 20 parameters for one call. See SDK
        #  docs. So send them in loop by bunches of 20 items
        keys = list(parameters.keys())
        while keys:
            query_keys = keys[:30]
            query = ','.join('{}={}'.format(k, parameters[k]) for k in query_keys).encode()
            del keys[:30]

            err = self.dll.SetDeviceParam(self.handle, query)
            if err < 0:
                raise ZKSDKError('SetDeviceParam failed', err)

    def __del__(self):
        self.disconnect()
