__all__ = [
    'User',
    'UserAuthorize',
    'Holiday',
    'Timezone',
    'Transaction',
    'FirstCard',
    'MultiCard',
    'InOutFun',
    'TemplateV10'
]

from datetime import date, time, datetime

from .common import ZKDatetimeUtils
from .device_data.model import Model, Field
from .enums import (
    HolidayLoop,
    VerifyMode,
    EVENT_TYPES,
    PassageDirection,
    INOUTFUN_OUTPUT,
    InOutFunRelayGroup,
    INOUTFUN_INPUT
)


class User(Model):
    """Card number information table"""
    table_name = 'user'

    card = Field('CardNo')
    pin = Field('Pin')
    password = Field('Password')
    group = Field('Group')
    start_time = Field(
        'StartTime', date, ZKDatetimeUtils.zkdate_to_date, ZKDatetimeUtils.date_to_zkdate
    )
    end_time = Field(
        'EndTime', date, ZKDatetimeUtils.zkdate_to_date, ZKDatetimeUtils.date_to_zkdate
    )
    super_authorize = Field('SuperAuthorize', bool, int, int)


class UserAuthorize(Model):
    """Access privilege list"""
    table_name = 'userauthorize'

    pin = Field('Pin')
    timezone_id = Field('AuthorizeTimezoneId', int)
    # tuple with 4 booleans (lock1..lock4)
    doors = Field(
        'AuthorizeDoorId',
        tuple,
        lambda x: (bool(i) for i in '{:04b}'.format(int(x))[::-1]),
        lambda x: int(''.join(str(int(i)) for i in x[::-1]), 2),
        lambda x: len(x) == 4
    )


class Holiday(Model):
    """Holiday table"""
    table_name = 'holiday'

    holiday = Field('Holiday')
    holiday_type = Field('HolidayType', int, None, None, lambda x: 1 <= x <= 3)
    loop = Field('Loop', HolidayLoop, int)


def _tz_encode(value: tuple):
    if all(isinstance(x, str) for x in value):
        value = tuple(datetime.strptime(x, '%Y-%m-%d') for x in value)

    return ZKDatetimeUtils.times_to_zktimerange(value[0], value[1])


_tz_decode = ZKDatetimeUtils.zktimerange_to_times


def _tz_validate(value: tuple) -> bool:
    return len(value) == 2 and all(isinstance(x, (time, datetime)) for x in value)


class Timezone(Model):
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


class Transaction(Model):
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


class FirstCard(Model):
    """First-card door opening"""
    table_name = 'firstcard'

    door = Field('DoorID', int)
    pin = Field('Pin')
    timezone_id = Field('TimezoneID', int)


class MultiCard(Model):
    """Multi-card door opening"""
    table_name = 'multimcard'   # Yes, typo in table name

    index = Field('Index')
    door = Field('DoorId', int)
    group1 = Field('Group1')
    group2 = Field('Group2')
    group3 = Field('Group3')
    group4 = Field('Group4')
    group5 = Field('Group5')


class InOutFun(Model):
    """Linkage control I/O table"""
    table_name = 'inoutfun'

    index = Field('Index')
    event_type = Field(
        'EventType', int, lambda x: EVENT_TYPES[int(x)], None, lambda x: x in EVENT_TYPES
    )
    input_index = Field(
        'InAddr', int, lambda x: INOUTFUN_INPUT[int(x)], None, lambda x: x in INOUTFUN_INPUT
    )
    is_output = Field('OutType', InOutFunRelayGroup)
    output_index = Field(
        'OutAddr',
        int,
        lambda x: INOUTFUN_OUTPUT[int(x)],
        None,
        lambda x: x in INOUTFUN_OUTPUT
    )
    time = Field('OutTime')  # FIXME: specify data type; can't test now
    reserved = Field('Reserved')


class TemplateV10(Model):
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
