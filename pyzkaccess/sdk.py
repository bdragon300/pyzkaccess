import ctypes
from typing import Iterable


class ZKSDK:
    def __init__(self, dllpath: str):
        self.dll = ctypes.WinDLL(dllpath)
        self.handle = None

    @property
    def is_connected(self) -> bool:
        return bool(self.handle is not None)

    def connect(self, connstr: bytes) -> None:
        self.handle = self.dll.Connect(connstr)
        if self.handle == 0:
            self.handle = None
            # FIXME: return errors description everywhere
            raise ConnectionError("Unable to connect device using connstr '{}'".format(connstr))

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
