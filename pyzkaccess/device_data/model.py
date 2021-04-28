__all__ = [
    'models_registry',
    'Field',
    'ModelMeta',
    'Model'
]

from enum import Enum
from typing import Mapping, MutableMapping, Callable, Optional, Type, TypeVar, Any

models_registry = {}  # type: MutableMapping[str, Type[Model]]


FieldDataT = TypeVar('FieldDataT')


class Field:
    """This class is used to define a field in Model. The property
    it assignes to will be used to access to an appropriate table field.
    In other words it provides object access to that field.

    Every field in device tables stores as a string, but some of
    them have a certain data format which could be represented
    with python types. Also some of them may have value restrictions.
    All of these parameters may be specified in Field definition as
    data type, convertion and validation callbacks. By default a
    field is treated as string with no restrictions.
    """
    def __init__(self,
                 raw_name: str,
                 field_datatype: Type = str,
                 get_cb: Optional[Callable[[str], Any]] = None,
                 set_cb: Optional[Callable[[Any], Any]] = None,
                 validation_cb: Optional[Callable[[FieldDataT], bool]] = None):
        """
        On getting a field value from Model record, the process is:
         1. Retrieve raw field value of `raw_name`. If nothing then
            just return None
         2. If `get_cb` is set then call it and use its result as value
         3. If value is not instance of `field_datatype` then try to
            cast it to this type
         4. Return value as field value

        On setting a field value in Model record, the process is:
         1. Check if value has `field_datatype` type, raise an error
            if not
         2. If `validation_cb` is set then call it, if result is false
            then raise an error
         3. Extract Enum value if value is Enum
         4. If `set_cb` is set then call it and use its result as value
         5. Write `str(value)` to raw field value of `raw_name`

        :param raw_name: field name in device table which this field
         associated to
        :param field_datatype: type of data of this field. `str` by
         default
        :param get_cb: optional callback that is called on field get
         before a raw string value will be converted to `field_datatype`
        :param set_cb: optional callback that is called on field set
         after value will be checked against `field_datatype`
         and validated by `validation_cb`
        :param validation_cb: optional callback that is called on
         field set after value will be checked against `field_datatype`.
         If returns false then validation will be failed
        """
        self._raw_name = raw_name
        self._field_datatype = field_datatype
        self._get_cb = get_cb
        self._set_cb = set_cb
        self._validation_cb = validation_cb

    @property
    def raw_name(self) -> str:
        """Raw field name in device table which this field
        associated to"""
        return self._raw_name

    def to_raw_value(self, value: Any) -> str:
        """Convert value of `field_datatype` to a raw string value.
        This function typically calls on field set.

        Checks incoming value against `field_datatype`, validates it
        using `validation_cb` (if any) and converts it using `set_cb`
        (if any).
        :param value: value of `field_datatype`
        :return: raw value string representation
        """
        if not isinstance(value, self._field_datatype):
            raise TypeError(
                'Bad value type {}, must be {}'.format(type(value), self._field_datatype)
            )

        if not(self._validation_cb is None or self._validation_cb(value)):
            raise ValueError('Value {} does not meet to field restrictions'.format(value))

        if isinstance(value, Enum):
            value = value.value

        if self._set_cb is not None:
            value = self._set_cb(value)

        return str(value)

    def to_field_value(self, value: str) -> FieldDataT:
        """Convert raw string value to a value of `field_datatype`.
        This function typically calls on field get.

        Converts incoming value using `get_cb` (if any). If
        type of value after that is not an instance of `field_datatype`,
        then tries to cast value to `field_datatype` (if specified).
        :param value: raw string representation
        :return: value of `field_datatype`
        """
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
            value = self.to_field_value(value)

        return value

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


class ModelMeta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['_fields_mapping'] = {}
        for attr_name, attr in attrs.items():
            if isinstance(attr, Field):
                attrs['_fields_mapping'][attr_name] = attr.raw_name

        klass = super(ModelMeta, mcs).__new__(mcs, name, bases, attrs)
        models_registry[name] = klass  # noqa
        return klass


class Model(metaclass=ModelMeta):
    """Base class for models that represent device data tables.

    A concrete model contains device table name and field definitions.
    Also it provides interface to access to these fields in a concrete
    row and to manipulate that row.
    """
    table_name = None

    _fields_mapping = None

    def __init__(self, **fields):
        """Accepts initial fields data in kwargs"""
        self._sdk = None
        self._dirty = True
        self._raw_data = {}  # type: Mapping[str, str]

        fm = self._fields_mapping
        if fields:
            unknown_fields = fields.keys() - fm.keys()
            if unknown_fields:
                raise TypeError('Unknown fields: {}'.format(tuple(unknown_fields)))

            self._raw_data = {
                fm[field]: getattr(self.__class__, field).to_raw_value(fields.get(field))
                for field in fm.keys() & fields.keys()
            }

    @property
    def dict(self) -> Mapping[str, FieldDataT]:
        """Return record data as a dict"""
        return {field: getattr(self, field) for field in self._fields_mapping.keys()}

    @property
    def raw_data(self) -> Mapping[str, str]:
        """Return raw data written directly to the device table on
        save"""
        return self._raw_data

    @classmethod
    def fields_mapping(cls) -> Mapping[str, str]:
        """Mapping between model fields and their raw fields"""
        return cls._fields_mapping

    def delete(self):
        """Delete this record from a table"""
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
        """Save changes in this record"""
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

    def with_raw_data(self, raw_data: Mapping[str, str], dirty: bool = True) -> 'Model':
        self._raw_data = raw_data
        self._dirty = dirty
        return self

    def with_sdk(self, sdk) -> 'Model':
        self._sdk = sdk
        return self

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self._raw_data == other._raw_data and self.table_name == other.table_name

    def __repr__(self):
        data = ', '.join(
            '{}={}'.format(f, self.raw_data.get(k))
            for f, k in sorted(self.fields_mapping().items())
        )
        return '{}{}({})'.format('*' if self._dirty else '', self.__class__.__name__, data)
