from datetime import datetime, time
from enum import Enum
from typing import Mapping, Any, MutableMapping, Callable, Optional, Type, Collection

from ..common import ZKDatetimeUtils
from ..enums import (
    HolidayLoop,
    VerifyMode,
    PassageDirection,
    EVENT_TYPES,
    TRANSACTIONS_INPUT,
    TRANSACTIONS_OUTPUT,
    TransactionsRelayGroup
)

data_table_classes = {}  # type: MutableMapping[str, Type[DataTable]]


class Field:
    def __init__(self,
                 raw_name: str,
                 field_datatype: Type = str,
                 get_cb: Optional[Callable[[Any], Any]] = None,
                 set_cb: Optional[Callable[[Any], Any]] = None,
                 validation_f: Optional[Callable[[Any], bool]] = None):
        self._raw_name = raw_name
        self._field_datatype = field_datatype
        self._get_cb = get_cb
        self._set_cb = set_cb
        self._validation_cb = validation_f

    @property
    def raw_name(self) -> str:
        return self._raw_name

    def to_raw_value(self, value: Any) -> str:
        # Check incoming value type. If prop_type is specified then
        # check against it, otherwise check against data_type
        if not isinstance(value, self._field_datatype):
            raise TypeError(
                'Bad value type {}, must be {}'.format(type(value), self._field_datatype)
            )

        # Pass original value to restriction function
        if not(self._validation_cb is None or self._validation_cb(value)):
            raise ValueError('Value {} does not meet to field restrictions'.format(value))

        if isinstance(value, Enum):
            value = value.value

        if self._set_cb is not None:
            value = self._set_cb(value)

        return str(value)

    def to_field_value(self, value: str) -> Any:
        if self._get_cb is not None:
            value = self._get_cb(value)
        if not isinstance(value, self._field_datatype):
            value = self._field_datatype(value)

        return value

    def __hash__(self):
        return hash(self._raw_name)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = instance._raw_data.get(self._raw_name)  # type: Optional[str]
        if value is not None:
            return self.to_field_value(value)

        return None

    def __set__(self, instance, value):
        if instance is None:
            return

        if value is None:
            self.__delete__(instance)
            return

        raw_value = self.to_raw_value(value)
        instance._raw_data[self._raw_name] = raw_value  # noqa
        instance._dirty = True

    def __delete__(self, instance):
        if instance is None:
            return

        if self._raw_name in instance._raw_data:
            del instance._raw_data[self._raw_name]
            instance._dirty = True


class DataTableMetadata(type):
    def __new__(mcs, name, bases, attrs):
        if '_fields_mapping' not in attrs:
            attrs['_fields_mapping'] = {}
            for attr_name, attr in attrs.items():
                if isinstance(attr, Field):
                    attrs['_fields_mapping'][attr_name] = attr.raw_name

        klass = super(DataTableMetadata, mcs).__new__(mcs, name, bases, attrs)
        data_table_classes[name] = klass  # noqa
        return klass


class DataTable(metaclass=DataTableMetadata):
    table_name = None

    def __init__(self, **fields):
        self._sdk = None
        self._dirty = True
        self._raw_data = {}

        fm = self._fields_mapping
        if fields:
            extra_keys = fields.keys() - fm.keys()
            if extra_keys:
                raise TypeError('Unknown fields: {}'.format(tuple(extra_keys)))

            self._raw_data = {
                fm[field]: getattr(self.__class__, field).to_raw_value(fields.get(field))
                for field in fm.keys() & fields.keys()
            }

    def delete(self):
        if self._sdk is None:
            raise TypeError('Unable to delete a manually created data table record')

        gen = self._sdk.delete_device_data(self.table_name)
        gen.send(None)
        gen.send(self.raw_data)
        try:
            gen.send(None)
        except StopIteration:
            pass

        self._dirty = True

    def save(self):
        if self._sdk is None:
            raise TypeError('Unable to save a manually created data table record')

        gen = self._sdk.set_device_data(self.table_name)
        gen.send(None)
        gen.send(self.raw_data)
        try:
            gen.send(None)
        except StopIteration:
            pass

        self._dirty = False

    @property
    def data(self) -> Mapping[str, Any]:
        return {field: self._raw_data.get(key)
                for field, key in self._fields_mapping.items()}

    @property
    def raw_data(self) -> Mapping[str, str]:
        return self._raw_data

    @classmethod
    def fields_mapping(cls) -> Mapping[str, str]:
        return cls._fields_mapping

    def with_raw_data(self, raw_data: Mapping[str, str], dirty: bool = True) -> 'DataTable':
        self._raw_data = raw_data
        self._dirty = dirty
        return self

    def with_sdk(self, sdk) -> 'DataTable':
        self._sdk = sdk
        return self

    def __repr__(self):
        return '{}{}({})'.format('*' if self._dirty else '',
                                 self.__class__.__name__,
                                 ', '.join('{}={}'.format(k, v) for k, v in self.data.items()))


class User(DataTable):
    """Card number information table"""
    table_name = 'user'

    card = Field('CardNo')
    pin = Field('Pin')
    password = Field('Password')
    group = Field('Group')
    # start_time = Field(  # FIXME: date only?
    #     'StartTime',
    #     datetime,
    #     ZKDatetimeUtils.zkctime_to_datetime,
    #     ZKDatetimeUtils.datetime_to_zkctime
    # )
    # end_time = Field(  # FIXME: date only?
    #     'EndTime',
    #     datetime,
    #     ZKDatetimeUtils.zkctime_to_datetime,
    #     ZKDatetimeUtils.datetime_to_zkctime
    # )
    start_time = Field(  # FIXME: date only?
        'StartTime'
    )
    end_time = Field(  # FIXME: date only?
        'EndTime'
    )
    super_authorize = Field('SuperAuthorize', bool, int, int)


class UserAuthorize(DataTable):
    """Access privilege list"""
    table_name = 'userauthorize'

    pin = Field('Pin')
    timezone_id = Field('AuthorizeTimezoneId', int)
    # tuple with 4 booleans (lock1..lock4)
    doors = Field(
        'AuthorizeDoorId',
        tuple,
        lambda x: (bool(i) for i in '{:04b}'.format(int(x))[::-1]),
        lambda x: int(''.join(x[::-1]), 2),
        lambda x: len(x) == 4
    )


class Holiday(DataTable):
    """Holiday table"""
    table_name = 'holiday'

    holiday = Field('Holiday')
    holiday_type = Field('HolidayType', int, None, None, lambda x: 1 <= x <= 3)
    loop = Field('Loop', HolidayLoop, int)


def _tz_encode(value: tuple):
    return ZKDatetimeUtils.times_to_zktimerange(value[0], value[1])


_tz_decode = ZKDatetimeUtils.zktimerange_to_times


def _tz_validate(value: tuple) -> bool:
    return len(value) == 2 and all(isinstance(x, (time, datetime)) for x in value)


class Timezone(DataTable):
    """Time zone table"""
    table_name = 'timezone'

    timezone_id = Field('TimezoneId')
    # Segment 1
    sun_time1 = Field('SunTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    mon_time1 = Field('MonTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    tue_time1 = Field('TueTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    wed_time1 = Field('WedTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    thu_time1 = Field('ThuTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    fri_time1 = Field('FriTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    sat_time1 = Field('SatTime1', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol1_time1 = Field('Hol1Time1', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol2_time1 = Field('Hol2Time1', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol3_time1 = Field('Hol3Time1', tuple, _tz_decode, _tz_encode, _tz_validate)
    # Segment 2
    sun_time2 = Field('SunTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    mon_time2 = Field('MonTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    tue_time2 = Field('TueTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    wed_time2 = Field('WedTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    thu_time2 = Field('ThuTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    fri_time2 = Field('FriTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    sat_time2 = Field('SatTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol1_time2 = Field('Hol1Time2', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol2_time2 = Field('Hol2Time2', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol3_time2 = Field('Hol3Time2', tuple, _tz_decode, _tz_encode, _tz_validate)
    # Segment 3
    sun_time3 = Field('SunTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    mon_time3 = Field('MonTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    tue_time3 = Field('TueTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    wed_time3 = Field('WedTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    thu_time3 = Field('ThuTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    fri_time3 = Field('FriTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    sat_time3 = Field('SatTime2', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol1_time3 = Field('Hol1Time3', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol2_time3 = Field('Hol2Time3', tuple, _tz_decode, _tz_encode, _tz_validate)
    hol3_time3 = Field('Hol3Time3', tuple, _tz_decode, _tz_encode, _tz_validate)


class Transaction(DataTable):
    """Access control record table"""
    table_name = 'transaction'

    card = Field('Cardno')
    pin = Field('Pin')
    verify_mode = Field('Verified', VerifyMode, int, int)
    door = Field('DoorID', int)
    event_type = Field(
        'EventType', int, lambda x: EVENT_TYPES[int(x)], None, lambda x: x in EVENT_TYPES
    )
    entry_exit = Field('InOutState', PassageDirection, int, int)
    time = Field(
        'Time_second',
        datetime,
        ZKDatetimeUtils.zkctime_to_datetime,
        ZKDatetimeUtils.datetime_to_zkctime
    )


class FirstCard(DataTable):
    """First-card door opening"""
    table_name = 'firstcard'

    door = Field('DoorID', int)
    pin = Field('Pin')
    timezone_id = Field('TimezoneID', int)


class MultiCard(DataTable):
    """Multi-card door opening"""
    table_name = 'multimcard'   # Yes, typo in table name

    index = Field('Index')
    door = Field('DoorId', int)
    group1 = Field('Group1')
    group2 = Field('Group2')
    group3 = Field('Group3')
    group4 = Field('Group4')
    group5 = Field('Group5')


class InOutFun(DataTable):
    """Linkage control I/O table"""
    table_name = 'inoutfun'

    index = Field('Index')
    event_type = Field(
        'EventType', int, lambda x: EVENT_TYPES[int(x)], None, lambda x: x in EVENT_TYPES
    )
    input_index = Field(
        'InAddr',
        int,
        lambda x: TRANSACTIONS_INPUT[int(x)],
        None,
        lambda x: x in TRANSACTIONS_INPUT
    )
    is_output = Field('OutType', TransactionsRelayGroup)
    output_index = Field(
        'OutAddr',
        int,
        lambda x: TRANSACTIONS_OUTPUT[int(x)],
        None,
        lambda x: x in TRANSACTIONS_OUTPUT
    )
    time = Field('OutTime')  # FIXME: specify data type; can't test now
    reserved = Field('Reserved')


class TemplateV10(DataTable):
    """templatev10 table. No information"""
    table_name = 'templatev10'

    size = Field('Size')
    uid = Field('UID')
    pin = Field('Pin')
    finger_id = Field('FingerID')
    valid = Field('Valid')
    template = Field('Template')
    resverd = Field('Resverd')
    end_tag = Field('EndTag')
