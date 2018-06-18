import ctypes
from .event import ZKRealtimeEvent


class ControlOperation:
    """
    Type of device control operation. See PULL SDK docs
    """
    output = 1
    cancel_alarm = 2
    restart = 3


class RelayGroup:
    """
    Device relay group. See PULL SDK docs
    """
    lock = 1
    aux = 2


class ZKAccess:
    @property
    def connstr(self):
        """Device connection string. Read only."""
        return self._connstr

    @property
    def dll_object(self):
        """DLL object. Read only."""
        return self._dll_object

    @property
    def handle(self):
        """Device handle. Has 'None' value if it's not connected to device. Read only."""
        return self._handle

    def __init__(self, dllpath, connstr=None):
        """
        Constructor. Takes path to DLL and device connection string.
        :param dllpath: Required. Full path to plcommpro.dll
        :param connstr: Optional. Device connection string. Connect will be performed if this specified.
        """
        self._handle = None
        self._connstr = None

        self._dll_object = ctypes.WinDLL(dllpath)

        if connstr:
            self.connect(connstr)

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

    def connect(self, connstr):
        """
        Connect to device using connection string, ex:
        'protocol=TCP,ipaddress=192.168.22.201,port=4370,timeout=4000,passwd='
        :param connstr: Device connection string
        :raises RuntimeError: if already connected
        :raises ConnectionError: connection attempt was unsuccessful
        :return:
        """
        if self._handle:
            raise RuntimeError('Already connected')

        self._connstr = connstr
        self._handle = self._dll_object.Connect(connstr)
        if self._handle == 0:
            self._handle = None
            raise ConnectionError("Unable to connect device using connstr '{}'".format(connstr))

    def disconnect(self):
        """
        Disconnect from device
        :return:
        """
        if not self._handle:
            return

        self._dll_object.Disconnect(self._handle)
        self._handle = None

    def enable_relay(self, group, number, timeout):
        """
        Enable specified relay for the given time. Already enabled relay keep its state, but timeout overwrites with new
        value.
        :param group: Relay group, see RelayGroup enum. Number between 1 and 4
        :param number: Relay number in specified group
        :param timeout: Seconds the relay will be enabled. Number between 0 and 255
        :raises ValueError: invalid parameter
        :raises RuntimeError: operation failed
        :return:
        """
        if number < 1 or number > 4:
            raise ValueError("Incorrect relay number: {}".format(number))
        if timeout < 0 or timeout > 255:
            raise ValueError("Incorrect timeout: {}".format(timeout))

        self.zk_control_device(
            ControlOperation.output,
            number,
            group,
            timeout,
            0
        )

    def enable_relay_list(self, l, timeout):
        """
        Enable relays by mask for the given time. Receives list with desired relays state: non-zero means enabled,
        zero means disabled. This action overwrites previous relays state.

        E.g. [1, 0, 0, 0, 0, 0, 1, 0] means 1, 7 relays get turned on in order as they placed on the device. Other
        ones get turned off.
        :param l: list with relays states
        :param timeout: Seconds the relay will be enabled. Number between 0 and 255
        :raises RuntimeError: operation failed
        :return:
        """
        relays = (1, 2, 3, 4, 1, 2, 3, 4)  # TODO: move to another class ZK400
        groups = (2, 2, 2, 2, 1, 1, 1, 1)  #
        # TODO: timeout check
        if len(l) != 8:  # TODO: change according to relays/groups
            raise ValueError('Relay list length is not 8')

        for i in range(8):
            if l[i]:
                self.zk_control_device(
                    ControlOperation.output,
                    relays[i],
                    groups[i],
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
        Device control machinery method. Read PULL SDK docs for parameters meaning
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
        :param buffer_size: Required. Buffer size in bytes that filled with contents
        :raises RuntimeError: if operation was failed
        :return: raw string with events
        """
        buf = ctypes.create_string_buffer(buffer_size)

        res = self.dll_object.GetRTLog(self.handle, buf, buffer_size)
        if res < 0:
            raise RuntimeError('GetRTLog failed, returned: {}'.format(str(res)))

        return buf.value.decode('utf-8')
