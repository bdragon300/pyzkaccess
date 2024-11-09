# pylint: disable=protected-access
__all__ = [
    "DaylightSavingMomentMode1",
    "DaylightSavingMomentMode2",
    "BaseParameters",
    "DeviceParameters",
    "DoorParameters",
]
import datetime
import re
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar

from pyzkaccess.common import ZKDatetimeUtils
from pyzkaccess.device import ZKModel
from pyzkaccess.enums import SensorType, VerifyMode
from pyzkaccess.sdk import ZKSDK

_DaylightSavingMomentMode1T = TypeVar("_DaylightSavingMomentMode1T", bound="DaylightSavingMomentMode1")


class DaylightSavingMomentMode1(datetime.datetime):
    """Daylight saving parameters used in mode1 setting (i.e. all parameters
    in one request). See `DLSTMode`, `DaylightSavingTime`,
    `StandardTime` parameters in SDK docs
    """

    # pylint: disable=signature-differs
    def __new__(cls, month: Optional[int] = None, day: Optional[int] = None, hour: int = 0, minute: int = 0) -> Any:
        return datetime.datetime.__new__(cls, 1970, month, day, hour, minute, 0)  # type: ignore

    def __repr__(self) -> str:
        return super().strftime("%m-%d %H:%M")

    def to_datetime(self) -> datetime.datetime:
        return datetime.datetime(1970, self.month, self.day, self.hour, self.minute)

    @classmethod
    def from_datetime(cls: Type[_DaylightSavingMomentMode1T], dt: datetime.datetime) -> _DaylightSavingMomentMode1T:
        return cls(month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)


def _make_daylight_prop(query_name_spring: str, query_name_fall: str, minimum: int, maximum: int) -> property:
    def read(self: "DaylightSavingMomentMode2") -> int:
        query = query_name_spring if self.is_daylight else query_name_fall
        if self._sdk is None:
            raise AttributeError("SDK is not set")

        params = self._sdk.get_device_param(parameters=(query,), buffer_size=self.buffer_size)
        res = int(params[query])
        if not minimum <= res <= maximum:
            raise ValueError(f"Value {res} is not in range {minimum}..{maximum}")

        return res

    def write(self: "DaylightSavingMomentMode2", value: int) -> None:
        query = query_name_spring if self.is_daylight else query_name_fall
        if not isinstance(value, int):
            raise TypeError("Bad value type, should be int")
        if not minimum <= value <= maximum:
            raise ValueError(f"Value {value} is not in range {minimum}..{maximum}")
        if self._sdk is None:
            raise AttributeError("SDK is not set")

        self._sdk.set_device_param(parameters={query: str(value)})

    return property(fget=read, fset=write, fdel=None, doc=None)


class DaylightSavingMomentMode2:
    """Daylight saving parameters used in mode2 setting (i.e. each parameter
    in a separate request). See `DLSTMode`, `WeekOfMonth*` parameters
    in SDK docs
    """

    def __init__(self, sdk: Optional[ZKSDK], is_daylight: bool, buffer_size: int):
        self.is_daylight = is_daylight
        self.buffer_size = buffer_size
        self._sdk = sdk

    month = _make_daylight_prop("WeekOfMonth1", "WeekOfMonth6", 1, 12)
    week_of_month = _make_daylight_prop("WeekOfMonth2", "WeekOfMonth7", 1, 6)
    day_of_week = _make_daylight_prop("WeekOfMonth3", "WeekOfMonth8", 0, 7)
    hour = _make_daylight_prop("WeekOfMonth4", "WeekOfMonth9", 0, 23)
    minute = _make_daylight_prop("WeekOfMonth5", "WeekOfMonth10", 0, 59)

    def __str__(self) -> str:
        pieces = "month", "week_of_month", "day_of_week", "hour", "minute"
        return f"{self.__class__.__name__}({', '.join(f'{x}={getattr(self, x)}' for x in pieces)})"

    def __repr__(self) -> str:
        return self.__str__()


PropTypeT = TypeVar("PropTypeT")


def _make_prop(
    query_tpl: str,
    data_type: Type,
    prop_type: Type[PropTypeT],
    readable: bool = True,
    writable: bool = True,
    doc: Optional[str] = None,
    restriction_f: Optional[Callable[[PropTypeT], bool]] = None,
) -> property:
    assert readable or writable

    def read(self: "BaseParameters") -> PropTypeT:
        query = query_tpl.format(self=self)
        params = self._sdk.get_device_param(parameters=(query,), buffer_size=self.buffer_size)
        param = params[query]
        prop = data_type(param)
        if data_type != prop_type:
            prop = prop_type(prop)  # type: ignore

        if not (restriction_f is None or restriction_f(prop)):
            raise ValueError(
                f"Value {prop} does not meet to parameter restrictions, " "see property docstring and SDK documentation"
            )

        return prop

    def write(self: "BaseParameters", value: PropTypeT) -> None:
        # Check incoming value type. If prop_type is specified then
        # check against it, otherwise check against data_type
        if not isinstance(value, prop_type):
            raise TypeError(f"Bad value type, should be {prop_type}")

        # Pass original value to restriction function
        if not (restriction_f is None or restriction_f(value)):
            raise ValueError(
                f"Value {value} does not meet to parameter restrictions, "
                "see property docstring and SDK documentation"
            )

        if issubclass(prop_type, Enum):
            value = value.value  # type: ignore
        data = data_type(value)

        query = query_tpl.format(self=self)
        self._sdk.set_device_param(parameters={query: str(data)})

    doc_readable_msg = "-".join(
        x
        for x in ["read" if readable else "", "write" if writable else "", "only" if readable != writable else ""]
        if x
    )
    return property(
        fget=read if readable else None,
        fset=write if writable else None,
        fdel=None,
        doc=f"{doc} ({doc_readable_msg})",
    )


class BaseParameters:
    buffer_size = 4096
    """Size in bytes of c-string buffer which is used to accept
    text data from PULL SDK functions"""

    def __init__(self, sdk: ZKSDK, device_model: Type[ZKModel]) -> None:
        self.device_model = device_model
        self._sdk = sdk


def _check_ip(addr: str) -> bool:
    return bool(
        re.match(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$", addr)
        and all(0 <= int(x) <= 255 for x in addr.split("."))
    )


class DeviceParameters(BaseParameters):
    serial_number = _make_prop("~SerialNumber", str, str, True, False, "Serial number of device")
    lock_count = _make_prop("LockCount", int, int, True, False, "Doors count")
    reader_count = _make_prop("ReaderCount", int, int, True, False, "Readers count")
    aux_in_count = _make_prop("AuxInCount", int, int, True, False, "Auxiliary inputs count")
    aux_out_count = _make_prop("AuxOutCount", int, int, True, False, "Auxiliary output count")
    communication_password = _make_prop(
        "ComPwd", str, str, True, True, "Password to connect to a device. Maximum is 15 symbols", lambda x: len(x) <= 15
    )
    ip_address = _make_prop("IPAddress", str, str, True, True, "Device IPv4 address", _check_ip)
    netmask = _make_prop("NetMask", str, str, True, True, "Subnet mask", _check_ip)
    gateway_ip_address = _make_prop("GATEIPAddress", str, str, True, True, "Gateway IPv4 address", _check_ip)
    rs232_baud_rate = _make_prop("RS232BaudRate", int, int, True, True, "RS232 baud rate", lambda x: x > 0)
    watchdog_enabled = _make_prop("WatchDog", int, bool, True, True, "MCU watchdog enabled")
    door4_to_door2 = _make_prop("Door4ToDoor2", int, bool, True, True, "4 doors turn 2 doors")
    backup_hour = _make_prop(
        "BackupTime", int, int, True, True, "The time (hour) of backup SD card. Number 1..24", lambda x: 1 <= x <= 24
    )
    reboot = _make_prop(
        "Reboot", int, bool, False, True, "Reboot a device, accepts only True value", lambda x: x is True
    )
    reader_direction = _make_prop("InBIOTowWay", str, str, True, True, "One-way/Two-way reader")
    display_daylight_saving = _make_prop("~DSTF", int, bool, True, True, "Display parameters of daylight saving time")
    enable_daylight_saving = _make_prop("DaylightSavingTimeOn", int, bool, True, True, "Enable time daylight saving")
    daylight_saving_mode = _make_prop(
        "DLSTMode",
        int,
        int,
        True,
        True,
        "Daylight saving mode, available values 0 (mode 1), 1 (mode 2)",
        lambda x: x in (0, 1),
    )

    @property
    def fingerprint_version(self) -> int:
        """Device fingerprint identification version. Available values: 9, 10 (read-only)"""
        params = self._sdk.get_device_param(parameters=("~ZKFPVersion",), buffer_size=self.buffer_size)
        str_res = params["~ZKFPVersion"]
        if str_res == "":
            return 0
        int_res = int(str_res)
        if int_res not in (9, 10):
            raise ValueError(f"Fingerprint version must be 9 or 10, got: {int_res}")

        return int_res

    @property
    def anti_passback_rule(self) -> int:
        """Passback rule for doors. Possible values depend on device
        model.

        Passback is when the second door can be opened only
        after the first door has opened, not otherwise. Or when a door
        can be opened only by its readers from one side.

        See `__doc__` value attribute to get a value meaning, ex::

            rule = zk.parameters.anti_passback_rule
            print(rule, 'means', rule.__doc__)
            # Prints "0 means Anti-passback disabled"
        """
        params = self._sdk.get_device_param(parameters=("AntiPassback",), buffer_size=self.buffer_size)
        int_res = int(params["AntiPassback"])
        if int_res not in self.device_model.anti_passback_rules:
            raise ValueError(
                f"Value {int_res} not in possible values for {self.device_model.name}: "
                f"{self.device_model.anti_passback_rules.keys()}"
            )

        return self.device_model.anti_passback_rules[int_res]

    @anti_passback_rule.setter
    def anti_passback_rule(self, value: int) -> None:
        if value not in self.device_model.anti_passback_rules:
            raise ValueError(
                f"Value {value} not in possible values for {self.device_model.name}: "
                f"{tuple(self.device_model.anti_passback_rules.keys())}"
            )
        self._sdk.set_device_param(parameters={"AntiPassback": str(value)})

    @property
    def interlock(self) -> int:
        """Interlock rule for doors. Possible values depend on device
        model.

        Interlock is the mode when you can open the second door only
        after *opening and closing* the first door, and vice versa.

        See `__doc__` value attribute to get a value meaning, ex::

            rule = zk.parameters.anti_passback_rule
            print(rule, 'means', rule.__doc__)
            # Prints "0 means Anti-passback disabled"
        """
        res = self._sdk.get_device_param(parameters=("InterLock",), buffer_size=self.buffer_size)
        if not res:
            return self.device_model.interlock_rules[0]

        int_res = int(res["InterLock"])
        if int_res not in self.device_model.interlock_rules:
            raise ValueError(
                f"Value {int_res} not in possible values for {self.device_model.name}: "
                f"{self.device_model.interlock_rules.keys()}"
            )
        return self.device_model.interlock_rules[int_res]

    @interlock.setter
    def interlock(self, value: int) -> None:
        if value not in self.device_model.anti_passback_rules:
            raise ValueError(
                f"Value {value} not in possible values for {self.device_model.name}: "
                f"{self.device_model.anti_passback_rules.keys()}"
            )
        self._sdk.set_device_param(parameters={"InterLock": str(value)})

    @property
    def spring_daylight_time_mode1(self) -> Optional[DaylightSavingMomentMode1]:
        """Spring forward daylight saving time (mode 1) (read-write)"""
        res = self._sdk.get_device_param(parameters=("DaylightSavingTime",), buffer_size=self.buffer_size)
        dt = ZKDatetimeUtils.zktimemoment_to_datetime(res["DaylightSavingTime"])
        if dt is not None:
            return DaylightSavingMomentMode1.from_datetime(dt)

        return None

    @spring_daylight_time_mode1.setter
    def spring_daylight_time_mode1(self, value: DaylightSavingMomentMode1) -> None:
        self._sdk.set_device_param(parameters={"DaylightSavingTime": ZKDatetimeUtils.datetime_to_zktimemoment(value)})

    @property
    def fall_daylight_time_mode1(self) -> Optional[DaylightSavingMomentMode1]:
        """Fall back daylight saving time (mode 1) (read-write)"""
        res = self._sdk.get_device_param(parameters=("StandardTime",), buffer_size=self.buffer_size)
        dt = ZKDatetimeUtils.zktimemoment_to_datetime(res["StandardTime"])
        if dt is not None:
            return DaylightSavingMomentMode1.from_datetime(dt)

        return None

    @fall_daylight_time_mode1.setter
    def fall_daylight_time_mode1(self, value: DaylightSavingMomentMode1) -> None:
        self._sdk.set_device_param(parameters={"StandardTime": ZKDatetimeUtils.datetime_to_zktimemoment(value)})

    @property
    def spring_daylight_time_mode2(self) -> DaylightSavingMomentMode2:
        """Spring forward daylight saving time (mode 2) (read-write)"""
        return DaylightSavingMomentMode2(self._sdk, True, self.buffer_size)

    @spring_daylight_time_mode2.setter
    def spring_daylight_time_mode2(self, value: DaylightSavingMomentMode2) -> None:
        t = DaylightSavingMomentMode2(self._sdk, True, self.buffer_size)
        for attr in ("month", "week_of_month", "day_of_week", "hour", "minute"):
            setattr(t, attr, getattr(value, attr))

    @property
    def fall_daylight_time_mode2(self) -> DaylightSavingMomentMode2:
        """Fall back daylight saving time (mode 2) (read-write)"""
        return DaylightSavingMomentMode2(self._sdk, False, self.buffer_size)

    @fall_daylight_time_mode2.setter
    def fall_daylight_time_mode2(self, value: DaylightSavingMomentMode2) -> None:
        t = DaylightSavingMomentMode2(self._sdk, False, self.buffer_size)
        for attr in ("month", "week_of_month", "day_of_week", "hour", "minute"):
            setattr(t, attr, getattr(value, attr))

    def _set_datetime(self, value: datetime.datetime) -> None:
        self._sdk.set_device_param(parameters={"DateTime": str(ZKDatetimeUtils.datetime_to_zkctime(value))})

    def _get_datetime(self) -> datetime.datetime:
        res = self._sdk.get_device_param(parameters=("DateTime",), buffer_size=self.buffer_size)
        int_res = int(res["DateTime"])
        return ZKDatetimeUtils.zkctime_to_datetime(int_res)

    datetime = property(_get_datetime, _set_datetime, None, "Current datetime (read-write)")


class DoorParameters(BaseParameters):
    """Parameters related to a concrete door"""

    def __init__(self, sdk: ZKSDK, device_model: Type[ZKModel], door_number: int) -> None:
        super().__init__(sdk, device_model)
        self.door_number = door_number

    duress_password = _make_prop(
        "Door{self.door_number}ForcePassWord",
        str,
        str,
        True,
        True,
        "Duress password for door. Maximum length is 8 digits",
        lambda x: x == "" or x.isdigit() and len(x) <= 8,
    )
    emergency_password = _make_prop(
        "Door{self.door_number}SupperPassWord",
        str,
        str,
        True,
        True,
        "Emergency password for door. Maximum length is 8 digits",
        lambda x: x == "" or x.isdigit() and len(x) <= 8,
    )
    lock_on_close = _make_prop("Door{self.door_number}CloseAndLock", int, bool, True, True, "Lock on door closing")
    sensor_type = _make_prop("Door{self.door_number}SensorType", int, SensorType, True, True, "Lock on door closing")
    lock_driver_time = _make_prop(
        "Door{self.door_number}Drivertime",
        int,
        int,
        True,
        True,
        "Lock driver time length. 0 - Normal closed, 1-254 - Door opening duration, 255 - Normal open",
        lambda x: 0 <= x <= 255,
    )
    magnet_alarm_duration = _make_prop(
        "Door{self.door_number}Detectortime",
        int,
        int,
        True,
        True,
        "Timeout alarm duration of door magnet",
        lambda x: 0 <= x <= 255,
    )
    verify_mode = _make_prop("Door{self.door_number}VerifyType", int, VerifyMode, True, True, "VerifyMode")
    multi_card_open = _make_prop(
        "Door{self.door_number}MultiCardOpenDoor", int, bool, True, True, "Open a door by several cards"
    )
    first_card_open = _make_prop(
        "Door{self.door_number}FirstCardOpenDoor", int, bool, True, True, "Open a door by first card"
    )
    active_time_tz = _make_prop(
        "Door{self.door_number}ValidTZ", int, int, True, True, "Active time segment for a door (0 - door is inactive)"
    )
    open_time_tz = _make_prop(
        "Door{self.door_number}KeepOpenTimeZone", int, int, True, True, "Normal-open time segment of door (0 - not set)"
    )
    punch_interval = _make_prop(
        "Door{self.door_number}Intertime", int, int, True, True, "Punch interval in seconds (0 - no interval)"
    )
    cancel_open_day = _make_prop(
        "Door{self.door_number}CancelKeepOpenDay", int, int, True, True, "The date of Cancel Normal Open"
    )
