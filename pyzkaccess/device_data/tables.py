from collections import namedtuple
from typing import Sequence, Optional, Mapping, Any, Type, Dict

QueryFilter = namedtuple('QueryFilter', ['field', 'operator', 'value'])

data_table_classes = {}  # type: Dict[str, Type[DataTable]]


class Field:
    def __init__(self, name: str, data_type: type = str):
        self._name = name
        self._data_type = data_type
        self._filters = []
        self._table_name = None

    @property
    def filters(self) -> Sequence[QueryFilter]:
        return self._filters

    @property
    def name(self) -> str:
        return self._name

    @property
    def table_name(self) -> str:
        return self._table_name

    @table_name.setter
    def table_name(self, value):
        self._table_name = value

    def copy(self) -> 'Field':
        res = self.__class__(self._name, self._data_type)
        res._filters = self._filters
        res._table_name = self._table_name
        return res

    def _add_filter(self, operation: str, value: Any) -> 'Field':
        if not isinstance(value, self._data_type):
            raise TypeError('Operation {}.{} {} {!r} only accepts argument type of {}'.format(
                self._table_name, self._name, operation, value, self._data_type
            ))
        res = self.copy()
        res._filters.append(QueryFilter(self._name, operation, value))
        return res

    def __hash__(self):
        return hash('{}.{}'.format(self._table_name, self._name))

    def __eq__(self, other) -> 'Field':
        return self._add_filter('==', other)

    def __ne__(self, other) -> 'Field':
        return self._add_filter('!=', other)

    def __and__(self, other) -> 'Field':
        if not isinstance(other, Field):
            raise TypeError("Operation {}.{} & {!r} only accepts argument type of Field".format(
                self._table_name, self._name, other
            ))
        res = self.copy()
        res._filters.extend(other._filters)
        return res

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return instance._data[self._name]

    def __set__(self, instance, value):
        if instance is None:
            return

        if not isinstance(value, self._data_type):
            raise TypeError('Value must be of type {}'.format(self._data_type))

        instance._data[self._name] = value


class DataTableMetadata(type):
    def __new__(mcs, name, bases, attrs):
        attrs['_fields_mapping'] = {}
        for attr_name, attr in attrs.items():
            if isinstance(attr, Field):
                attr.table_name = attrs['table_name']
                attrs['_fields_mapping'][attr_name] = attr.name

        print(attrs)
        print(name)
        klass = super(DataTableMetadata, mcs).__new__(mcs, name, bases, attrs)
        data_table_classes[name] = klass
        return klass


class DataTable(metaclass=DataTableMetadata):
    table_name = None

    def __init__(self, **fields):
        self._data = {}
        if fields:
            self._data = {self._fields_mapping[field]: fields[field]
                          for field in fields.keys() & self._fields_mapping.keys()}

    @property
    def data(self):
        return {field: self._data.get(key)
                for field, key in self._fields_mapping.items()}

    def with_raw_data(self, data: Mapping[str, Any]) -> 'DataTable':
        self._data = data
        return self

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               ', '.join('{}={}'.format(k, v) for k, v in self.data.items()))


class User(DataTable):
    """Card number information table"""
    table_name = 'user'
    field1 = Field('field1')
    field2 = Field('field2')


class UserAuthorize(DataTable):
    """Access privilege list"""
    table_name = 'userauthorize'
    field1 = Field('field1')
    field2 = Field('field2')


class Holiday(DataTable):
    """Holiday table"""
    table_name = 'holiday'
    field1 = Field('field1')
    field2 = Field('field2')


class Timezone(DataTable):
    """Time zone table"""
    table_name = 'timezone'
    field1 = Field('field1')
    field2 = Field('field2')


class Transaction(DataTable):
    """Access control record table"""
    table_name = 'transaction'
    card = Field('Cardno')
    pin = Field('Pin')
    verify_mode = Field('Verified')
    door = Field('DoorID')
    event_type = Field('EventType')
    entry_exit = Field('InOutState')
    time = Field('Time_second')


class FirstCard(DataTable):
    """First-card door opening"""
    table_name = 'firstcard'
    field1 = Field('field1')
    field2 = Field('field2')


class Multicard(DataTable):
    """Multi-card door opening"""
    table_name = 'multicard'
    field1 = Field('field1')
    field2 = Field('field2')


class InOutFun(DataTable):
    """Linkage control I/O table"""
    table_name = 'inoutfun'
    field1 = Field('field1')
    field2 = Field('field2')


class TemplateV10(DataTable):
    """templatev10 table ?"""
    table_name = 'templatev10'
    field1 = Field('field1')
    field2 = Field('field2')
