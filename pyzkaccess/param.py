__all__ = [
    'DaylightSavingMomentMode1',
    'DaylightSavingMomentMode2',
    'BaseParameters',
    'DeviceParameters',
    'DoorParameters'
]
import re
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import ZKDatetimeUtils
from .device import ZKModel
from .enums import SensorType, VerifyMode
from .sdk import ZKSDK


def _make_daylight_prop(query_name_spring, query_name_fall, minimum, maximum):
    def read(self) -> int:
        query = query_name_spring if self.is_daylight else query_name_fall
        res = self._sdk.get_device_param(parameters=(query,), buffer_size=self.buffer_size)
        res = int(res[query])
        if not(minimum <= res <= maximum):
            raise ValueError('Value {} is not in range {}..{}'.format(res, minimum, maximum))

        return res

    def write(self, value: int):
        query = query_name_spring if self.is_daylight else query_name_fall
        if not isinstance(value, int):
            raise TypeError('Bad value type, should be int')
        if not(minimum <= value <= maximum):
            raise ValueError('Value {} is not in range {}..{}'.format(value, minimum, maximum))

        self._sdk.set_device_param(parameters={query: str(value)})

    return property(fget=read, fset=write, fdel=None, doc=None)


class DaylightSavingMomentMode1:
    """Daylight saving parameters used in mode1 setting (all parameters
    in one request). See `DLSTMode`, `DaylightSavingTime`,
    `StandardTime` parameters in SDK docs
    """
    def __init__(self, month, day, hour, minute):
        self.month = int(month)
        self.day = int(day)
        self.hour = int(hour)
        self.minute = int(minute)

        if not(1 <= self.month <= 12):
            raise ValueError('Month must have value in range 1..12')
        if not(1 <= self.day <= 7):
            raise ValueError('Day of week must have value in range 1..7')
        if not(0 <= self.hour <= 23):
            raise ValueError('Hour must have value in range 0..23')
        if not(0 <= self.minute <= 59):
            raise ValueError('Minute must have value in range 0..59')

    def __str__(self):
        return '-'.join(str(x) for x in (self.month, self.day, self.hour, self.minute))

    def __repr__(self):
        pieces = 'month', 'day', 'hour', 'minute'
        return '{}({})'.format(self.__class__.__name__,
                               ', '.join('{}={}'.format(x, getattr(self, x)) for x in pieces))


class DaylightSavingMomentMode2:
    """Daylight saving parameters used in mode2 setting (each parameter
    in a separate request). See `DLSTMode`, `WeekOfMonth*` parameters
    in SDK docs
    """
    def __init__(self, sdk: Optional[ZKSDK], is_daylight: bool, buffer_size: int):
        self.is_daylight = is_daylight
        self.buffer_size = buffer_size
        self._sdk = sdk

    month = _make_daylight_prop('WeekOfMonth1', 'WeekOfMonth6', 1, 12)
    week_of_month = _make_daylight_prop('WeekOfMonth2', 'WeekOfMonth7', 1, 6)
    day_of_week = _make_daylight_prop('WeekOfMonth3', 'WeekOfMonth8', 1, 7)
    hour = _make_daylight_prop('WeekOfMonth4', 'WeekOfMonth9', 0, 23)
    minute = _make_daylight_prop('WeekOfMonth5', 'WeekOfMonth10', 0, 59)

    def __str__(self):
        pieces = 'month', 'week_of_month', 'day_of_week', 'hour', 'minute'
        return '{}({})'.format(self.__class__.__name__,
                               ', '.join('{}={}'.format(x, getattr(self, x)) for x in pieces))

    def __repr__(self):
        return self.__str__()


def _make_prop(query_tpl: str,
               data_type,
               prop_type,
               readable=True,
               writable=True,
               doc=None,
               restriction_f=None):
    assert readable or writable

    def read(self) -> prop_type:
        query = query_tpl.format(self=self)
        res = self._sdk.get_device_param(parameters=(query,), buffer_size=self.buffer_size)
        res = res[query]
        res = data_type(res)
        if data_type != prop_type:
            res = prop_type(res)

        if not(restriction_f is None or restriction_f(res)):
            raise ValueError('Value {} does not meet to parameter restrictions, '
                             'see property docstring and SDK documentation'.format(res))

        return res

    def write(self, value: prop_type):
        # Check incoming value type. If prop_type is specified then
        # check against it, otherwise check against data_type
        if not isinstance(value, prop_type):
            raise TypeError('Bad value type, should be {}'.format(prop_type))

        # Pass original value to restriction function
        if not(restriction_f is None or restriction_f(value)):
            raise ValueError('Value {} does not meet to parameter restrictions, '
                             'see property docstring and SDK documentation'.format(value))

        if issubclass(prop_type, Enum):
            value = value.value
        value = data_type(value)

        query = query_tpl.format(self=self)
        self._sdk.set_device_param(parameters={query: str(value)})

    doc_readable_msg = '-'.join(x for x in [
        'read' if readable else '',
        'write' if writable else '',
        'only' if readable != writable else ''
    ] if x)
    return property(
        fget=read if readable else None,
        fset=write if writable else None,
        fdel=None,
        doc='{} ({})'.format(doc, doc_readable_msg)
    )


class BaseParameters:
    buffer_size = 4096
    """Size in bytes of c-string buffer which is used to accept
    text data from PULL SDK functions"""

    def __init__(self, sdk: ZKSDK, device_model: type(ZKModel)):
        self.device_model = device_model
        self._sdk = sdk


def _check_ip(addr: str):
    return re.match(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', addr) \
           and all(0 <= int(x) <= 255 for x in addr.split('.'))


class DeviceParameters(BaseParameters):
    serial_number = _make_prop(
        '~SerialNumber', str, str, True, False, 'Serial number of device'
    )
    lock_count = _make_prop('LockCount', int, int, True, False, 'Doors count')
    reader_count = _make_prop('ReaderCount', int, int, True, False, 'Readers count')
    aux_in_count = _make_prop('AuxInCount', int, int, True, False, 'Auxiliary inputs count')
    aux_out_count = _make_prop('AuxOutCount', int, int, True, False, 'Auxiliary output count')
    communication_password = _make_prop(
        'ComPwd', str, str, True, True,
        'Password to connect to a device. Maximum is 15 symbols',
        lambda x: len(x) <= 15
    )
    ip_address = _make_prop('IPAddress', str, str, True, True, 'Device IPv4 address', _check_ip)
    netmask = _make_prop('NetMask', str, str, True, True, 'Subnet mask', _check_ip)
    gateway_ip_address = _make_prop(
        'GATEIPAddress', str, str, True, True,  'Gateway IPv4 address', _check_ip
    )
    rs232_baud_rate = _make_prop(
        'RS232BaudRate', int, int, True, True, 'RS232 baud rate', lambda x: x > 0
    )
    watchdog_enabled = _make_prop('WatchDog', int, bool, True, True, 'MCU watchdog enabled')
    door4_to_door2 = _make_prop('Door4ToDoor2', int, bool, True, True, '4 doors turn 2 doors')
    backup_hour = _make_prop(
        'BackupTime', int, int, True, True,
        'The time (hour) of backup SD card. Number 1..24',
        lambda x: 1 <= x <= 24
    )
    reboot = _make_prop(
        'Reboot', int, bool, False, True,
        'Reboot a device, accepts only True value',
        lambda x: x is True
    )
    reader_direction = _make_prop('InBIOTowWay', str, str, True, True, 'One-way/Two-way reader')
    fingerprint_version = _make_prop(
        '~ZKFPVersion', int, int, True, False,
        'Device fingerprint identification version. Available values: 9, 10',
        lambda x: x in (9, 10)
    )
    display_daylight_saving = _make_prop(
        '~DSTF', int, bool, True, True, 'Display parameters of daylight saving time'
    )
    enable_daylight_saving = _make_prop(
        'DaylightSavingTimeOn', int, bool, True, True, 'Enable time daylight saving'
    )
    daylight_saving_mode = _make_prop(
        'DLSTMode', int, int, True, True,
        'Daylight saving mode, available values 0 (mode 1), 1 (mode 2)',
        lambda x: x in (0, 1)
    )

    @property
    def anti_passback_rule(self) -> int:
        """Passback rule for doors. Possible values depend on device
        model. Passback is when the second door can be opened only
        after the first door has opened, not otherwise. Or a door
        can be opened only by its readers from one side.

        See `__doc__` value attribute to get a value meaning, ex::

            rule = zk.parameters.anti_passback_rule
            print(rule, 'means', rule.__doc__)
            # Prints "0 means Anti-passback disabled"
        """
        res = self._sdk.get_device_param(parameters=('AntiPassback',), buffer_size=self.buffer_size)
        res = int(res['AntiPassback'])
        if res not in self.device_model.anti_passback_rules:
            raise ValueError('Value {} not in possible values for {}: {}'.format(
                res, self.device_model.name, self.device_model.anti_passback_rules.keys()
            ))

        return self.device_model.anti_passback_rules[res]

    @anti_passback_rule.setter
    def anti_passback_rule(self, value: int):
        if value not in self.device_model.anti_passback_rules:
            raise ValueError('Value {} not in possible values for {}: {}'.format(
                value, self.device_model.name, tuple(self.device_model.anti_passback_rules.keys())
            ))
        self._sdk.set_device_param(parameters={'AntiPassback': str(value)})

    @property
    def interlock(self) -> int:
        """Interlock rule for doors. Possible values depend on device
        model. Interlock is when the second door can be opened only
        after the first door was opened and closed, and vice versa

        See `__doc__` value attribute to get a value meaning, ex::

            rule = zk.parameters.anti_passback_rule
            print(rule, 'means', rule.__doc__)
            # Prints "0 means Anti-passback disabled"
        """
        res = self._sdk.get_device_param(parameters=('InterLock',), buffer_size=self.buffer_size)
        if not res:
            return self.device_model.interlock_rules[0]

        res = int(res['InterLock'])
        if res not in self.device_model.interlock_rules:
            raise ValueError('Value {} not in possible values for {}: {}'.format(
                res, self.device_model.name, self.device_model.interlock_rules.keys()
            ))
        return self.device_model.interlock_rules[res]

    @interlock.setter
    def interlock(self, value: int):
        if value not in self.device_model.anti_passback_rules:
            raise ValueError('Value {} not in possible values for {}: {}'.format(
                value, self.device_model.name, self.device_model.anti_passback_rules.keys()
            ))
        self._sdk.set_device_param(parameters={'InterLock': str(value)})

    @property
    def spring_daylight_time_mode1(self) -> DaylightSavingMomentMode1:
        """Spring forward daylight saving time (mode 1) (read-write)"""
        res = self._sdk.get_device_param(parameters=('DaylightSavingTime',),
                                         buffer_size=self.buffer_size)
        res = [int(x) for x in res['DaylightSavingTime'].split('-')]  # FIXME: extract bytes?
        return DaylightSavingMomentMode1(month=res[0], day=res[1], hour=res[2], minute=res[3])

    @spring_daylight_time_mode1.setter
    def spring_daylight_time_mode1(self, value: DaylightSavingMomentMode1):
        self._sdk.set_device_param(parameters={'DaylightSavingTime': str(value)})

    @property
    def fall_daylight_time_mode1(self) -> DaylightSavingMomentMode1:
        """Fall back daylight saving time (mode 1) (read-write)"""
        res = self._sdk.get_device_param(parameters=('StandardTime',), buffer_size=self.buffer_size)
        res = [int(x) for x in res['StandardTime'].split('-')]
        return DaylightSavingMomentMode1(month=res[0], day=res[1], hour=res[2], minute=res[3])

    @fall_daylight_time_mode1.setter
    def fall_daylight_time_mode1(self, value: DaylightSavingMomentMode1):
        self._sdk.set_device_param(parameters={'StandardTime': str(value)})

    @property
    def spring_daylight_time_mode2(self) -> DaylightSavingMomentMode2:
        """Spring forward daylight saving time (mode 2) (read-write)"""
        return DaylightSavingMomentMode2(self._sdk, True, self.buffer_size)

    @spring_daylight_time_mode2.setter
    def spring_daylight_time_mode2(self, value: DaylightSavingMomentMode2):
        t = DaylightSavingMomentMode2(self._sdk, True, self.buffer_size)
        for attr in ('month', 'week_of_month', 'day_of_week', 'hour', 'minute'):
            setattr(t, attr, getattr(value, attr))

    @property
    def fall_daylight_time_mode2(self) -> DaylightSavingMomentMode2:
        """Fall back daylight saving time (mode 2) (read-write)"""
        return DaylightSavingMomentMode2(self._sdk, False, self.buffer_size)

    @fall_daylight_time_mode2.setter
    def fall_daylight_time_mode2(self, value: DaylightSavingMomentMode2):
        t = DaylightSavingMomentMode2(self._sdk, False, self.buffer_size)
        for attr in ('month', 'week_of_month', 'day_of_week', 'hour', 'minute'):
            setattr(t, attr, getattr(value, attr))

    def _set_datetime(self, value: datetime):
        self._sdk.set_device_param(
            parameters={'DateTime': str(ZKDatetimeUtils.datetime_to_zkctime(value))}
        )

    def _get_datetime(self) -> datetime:
        res = self._sdk.get_device_param(parameters=('DateTime',), buffer_size=self.buffer_size)
        res = int(res['DateTime'])
        return ZKDatetimeUtils.zkctime_to_datetime(res)

    datetime = property(_get_datetime, _set_datetime, None, 'Current datetime (read-write)')


class DoorParameters(BaseParameters):
    """Parameters related to a concrete door"""
    def __init__(self, sdk: ZKSDK, device_model: type(ZKModel), door_number: int):
        super().__init__(sdk, device_model)
        self.door_number = door_number

    duress_password = _make_prop(
        'Door{self.door_number}ForcePassWord', str, str, True, True,
        'Duress password for door. Maximum length is 8 digits',
        lambda x: x == '' or x.isdigit() and len(x) <= 8
    )
    emergency_password = _make_prop(
        'Door{self.door_number}SupperPassWord', str, str, True, True,
        'Emergency password for door. Maximum length is 8 digits',
        lambda x: x == '' or x.isdigit() and len(x) <= 8
    )
    lock_on_close = _make_prop(
        'Door{self.door_number}CloseAndLock', int, bool, True, True, 'Lock on door closing'
    )
    sensor_type = _make_prop(
        'Door{self.door_number}SensorType', int, SensorType, True, True, 'Lock on door closing'
    )
    lock_driver_time = _make_prop(
        'Door{self.door_number}Drivertime', int, int, True, True,
        'Lock driver time length. 0 - Normal closed, 1-254 - Door opening duration, '
        '255 - Normal open',
        lambda x: 0 <= x <= 255
    )
    magnet_alarm_duration = _make_prop(
        'Door{self.door_number}Detectortime', int, int, True, True,
        'Timeout alarm duration of door magnet',
        lambda x: 0 <= x <= 255
    )
    verify_mode = _make_prop(
        'Door{self.door_number}VerifyType', int, VerifyMode, True, True, 'VerifyMode'
    )
    multi_card_open = _make_prop(
        'Door{self.door_number}MultiCardOpenDoor', int, bool, True, True,
        'Open a door by several cards'
    )
    first_card_open = _make_prop(
        'Door{self.door_number}FirstCardOpenDoor', int, bool, True, True,
        'Open a door by first card'
    )
    active_time_tz = _make_prop(
        'Door{self.door_number}ValidTZ', int, int, True, True,
        'Active time segment for a door (0 - door is inactive)'
    )
    open_time_tz = _make_prop(
        'Door{self.door_number}KeepOpenTimeZone', int, int, True, True,
        'Normal-open time segment of door (0 - not set)'
    )
    punch_interval = _make_prop(
        'Door{self.door_number}Intertime', int, int, True, True,
        'Punch interval in seconds (0 - no interval)'
    )
    cancel_open_day = _make_prop(
        'Door{self.door_number}CancelKeepOpenDay', int, int, True, True,
        'The date of Cancel Normal Open'
    )
