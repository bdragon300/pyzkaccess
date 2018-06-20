import ctypes
from datetime import datetime


#
# Enumerations
#


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


VERIFY_MODES = {
    '1':   'Only finger',
    '3':   'Only password',
    '4':   'Only card',
    '11':  'Card and password',
    '200': 'Others'
}

EVENT_TYPES = {
    '0':   'Normal Punch Open',
    '1':   'Punch during Normal Open Time Zone',
    '2':   'First Card Normal Open (Punch Card)',
    '3':   'Multi-Card Open (Punching Card)',
    '4':   'Emergency Password Open',
    '5':   'Open during Normal Open Time Zone',
    '6':   'Linkage Event Triggered',
    '7':   'Cancel Alarm',
    '8':   'Remote Opening',
    '9':   'Remote Closing',
    '10':  'Disable Intraday Normal Open Time Zone',
    '11':  'Enable Intraday Normal Open Time Zone',
    '12':  'Open Auxiliary Output',
    '13':  'Close Auxiliary Output',
    '14':  'Press Fingerprint Open',
    '15':  'Multi-Card Open (Press Fingerprint)',
    '16':  'Press Fingerprint during Normal Open Time Zone',
    '17':  'Card plus Fingerprint Open',
    '18':  'First Card Normal Open (Press Fingerprint)',
    '19':  'First Card Normal Open (Card plus Fingerprint)',
    '20':  'Too Short Punch Interval',
    '21':  'Door Inactive Time Zone (Punch Card)',
    '22':  'Illegal Time Zone',
    '23':  'Access Denied',
    '24':  'Anti-Passback',
    '25':  'Interlock',
    '26':  'Multi-Card Authentication (Punching Card)',
    '27':  'Unregistered Card',
    '28':  'Opening Timeout',
    '29':  'Card Expired',
    '30':  'Password Error',
    '31':  'Too Short Fingerprint Pressing Interval',
    '32':  'Multi-Card Authentication (Press Fingerprint)',
    '33':  'Fingerprint Expired',
    '34':  'Unregistered Fingerprint',
    '35':  'Door Inactive Time Zone (Press Fingerprint)',
    '36':  'Door Inactive Time Zone (Exit Button)',
    '37':  'Failed to Close during Normal Open Time Zone',
    '101': 'Duress Password Open',
    '102': 'Opened Accidentally',
    '103': 'Duress Fingerprint Open',
    '200': 'Door Opened Correctly',
    '201': 'Door Closed Correctly',
    '202': 'Exit button Open',
    '203': 'Multi-Card Open (Card plus Fingerprint)',
    '204': 'Normal Open Time Zone Over',
    '205': 'Remote Normal Opening',
    '220': 'Auxiliary Input Disconnected',
    '221': 'Auxiliary Input Shorted',
    '255': 'Actually that obtain door status and alarm status',
}

ENTRY_EXIT_TYPES = {
    '0': 'Entry',
    '1': 'Exit',
    '2': 'None'
}


#
# Device model-specific classes
#

class ZK400:
    """ZKAccess C3-400"""
    relays = 8
    relays_def = (
        1, 2, 3, 4,
        1, 2, 3, 4
    )
    groups_def = (
        RelayGroup.aux,  RelayGroup.aux,  RelayGroup.aux,  RelayGroup.aux,
        RelayGroup.lock, RelayGroup.lock, RelayGroup.lock, RelayGroup.lock
    )


class ZK200:
    """ZKAccess C3-200"""
    relays = 4
    relays_def = (1, 2, 1, 2)
    groups_def = (RelayGroup.aux,  RelayGroup.aux, RelayGroup.lock, RelayGroup.lock)


class ZK100:
    """ZKAccess C3-100"""
    relays = 2
    relays_def = (1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.lock)


#
# Main class
#


class ZKAccess:
    """
    Main class to work on. Contains interface for working with device, implements SDK calls and holds current state
    """
    @property
    def device_model(self):
        """Device model class. Read only"""
        return self._device_model

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

    def __init__(self, dllpath, connstr=None, device_model=ZK400):
        """
        Constructor. Takes path to DLL and device connection string.
        :param dllpath: Required. Full path to plcommpro.dll
        :param connstr: Optional. Device connection string. Connect will be performed if this specified.
        :param device_model: Optional. Device model class. Default is ZK400
        """
        self._handle = None
        self._connstr = None
        self._device_model = device_model

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
        if number < 1 or number > self.device_model.relays:
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
                    self.device_model.groups_def[i],
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
