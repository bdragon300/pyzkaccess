from typing import Mapping, Any, Type, MutableMapping, AbstractSet

data_table_classes = {}  # type: MutableMapping[str, Type[DataTable]]


class Field:
    def __init__(self, raw_name: str, data_type: type = str):
        self._raw_name = raw_name
        self._data_type = data_type

    @property
    def raw_name(self) -> str:
        return self._raw_name

    def __hash__(self):
        return hash(self._raw_name)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return instance._data[self._raw_name]

    def __set__(self, instance, value):
        if instance is None:
            return

        if not isinstance(value, self._data_type):
            value = self._data_type(value)

        instance._data[self._raw_name] = value
        instance._dirty = True


class DataTableMetadata(type):
    def __new__(mcs, name, bases, attrs):
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
        self._data = {}
        if fields:
            self._data = {self._fields_mapping[field]: fields[field]
                          for field in fields.keys() & self._fields_mapping.keys()}

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
        return {field: self._data.get(key)
                for field, key in self._fields_mapping.items()}

    @property
    def raw_data(self) -> Mapping[str, str]:
        return self._data  # TODO: cast to str

    @classmethod
    def fields_mapping(cls) -> Mapping[str, str]:
        return cls._fields_mapping

    def with_raw_data(self, data: Mapping[str, str], dirty: bool = True) -> 'DataTable':
        self._data = data  # TODO: cast to field types
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
    start_time = Field('StartTime')  # TODO: datetime
    end_time = Field('EndTime')  # TODO: datetime
    super_authorize = Field('SuperAuthorize')  # TODO: zkbool


class UserAuthorize(DataTable):
    """Access privilege list"""
    table_name = 'userauthorize'
    pin = Field('Pin')
    timezone_id = Field('AuthorizeTimezoneId', int)
    door = Field('AuthorizeDoorId')  # TODO: new type with doors device-specific combinations (bitmask)


class Holiday(DataTable):
    """Holiday table"""
    table_name = 'holiday'
    holiday = Field('Holiday')
    holiday_type = Field('HolidayType')  # TODO: 1,2,3 (meanings?)
    loop = Field('Loop')  # TODO: DocDict with ints


class Timezone(DataTable):
    """Time zone table"""
    table_name = 'timezone'

    def with_raw_data(self, data: Mapping[str, Any]) -> 'DataTable':
        return super().with_raw_data(data)

    timezone_id = Field('TimezoneId')
    segment1 = Field('_')  # TODO: sun-sat, hol1-hol3
    segment2 = Field('_')  #
    segment3 = Field('_')  #


class Transaction(DataTable):
    """Access control record table"""
    table_name = 'transaction'
    card = Field('Cardno')
    pin = Field('Pin')
    verify_mode = Field('Verified')  # TODO: enum
    door = Field('DoorID', int)
    event_type = Field('EventType')  # TODO: enum
    entry_exit = Field('InOutState')  # TODO: enum
    time = Field('Time_second')  # TODO: datetime


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
    event_type = Field('EventType')  # TODO: DocDict
    input_index = Field('InAddr')  # TODO: DocDict
    is_output = Field('OutType')  # TODO: DocDict
    output_index = Field('OutAddr')  # TODO: DocDict
    time = Field('OutTime')  # TODO: datetime
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
