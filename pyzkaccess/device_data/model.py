# pylint: disable=cyclic-import
__all__ = ["models_registry", "Field", "ModelMeta", "Model"]

from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Mapping,
    MutableMapping,
    Optional,
    Type,
    TypeVar,
    cast,
    overload,
)

from pyzkaccess.sdk import ZKSDK

if TYPE_CHECKING:
    from pyzkaccess.main import ZKAccess

models_registry: MutableMapping[str, Type["Model"]] = {}


_FieldDataT = TypeVar("_FieldDataT")


class Field(Generic[_FieldDataT]):
    """This class is for internal use. It defines a field and its
    options in data table model definition.

    The main aim of this class is to validate, decode and cast the
    raw string field value coming from the device to a python type.
    In contrary, it validates, casts the python type to a raw string
    and encodes it to write it to the device on demand.
    """

    @overload
    def __init__(self, raw_name: str, field_datatype: Type[_FieldDataT]): ...

    @overload
    def __init__(self, raw_name: str, field_datatype: Type[_FieldDataT], get_cb: Optional[Callable[[str], Any]]): ...

    @overload
    def __init__(
        self,
        raw_name: str,
        field_datatype: Type[_FieldDataT],
        get_cb: Optional[Callable[[str], Any]],
        set_cb: Optional[Callable[[Any], Any]],
    ): ...

    @overload
    def __init__(  # pylint: disable=too-many-arguments
        self,
        raw_name: str,
        field_datatype: Type[_FieldDataT],
        get_cb: Optional[Callable[[str], Any]],
        set_cb: Optional[Callable[[Any], Any]],
        validation_cb: Optional[Callable[[_FieldDataT], bool]],
    ): ...

    def __init__(  # pylint: disable=too-many-arguments
        self,
        raw_name: str,
        field_datatype: Type[_FieldDataT],
        get_cb: Optional[Callable[[str], Any]] = None,
        set_cb: Optional[Callable[[Any], Any]] = None,
        validation_cb: Optional[Callable[[_FieldDataT], bool]] = None,
    ):
        """Construct a Model field.

        Args:
            raw_name (str): field name in device table which this field
                associated to
            field_datatype (Type[FieldDataT]): type of data of this field.
            get_cb (Callable[[str], Any], optional): callback that is
                called on field get before a raw string value will be
                converted to `field_datatype`
            set_cb (Callable[[Any], Any], optional): callback
                that is called on field set after value will be checked
                against `field_datatype` and validated by
                `validation_cb`
            validation_cb (Callable[[FieldDataT], bool], optional): this
                is a callback that is called on field set after
                value will be checked against `field_datatype`. If
                returns false then validation will be failed

        """
        self._raw_name = raw_name
        self._field_datatype: Type[_FieldDataT] = field_datatype
        self._get_cb = get_cb
        self._set_cb = set_cb
        self._validation_cb = validation_cb

    @property
    def raw_name(self) -> str:
        """Raw field name in device table which this field
        associated to
        """
        return self._raw_name

    @property
    def field_datatype(self) -> Type[_FieldDataT]:
        """Field data type"""
        return self._field_datatype

    def to_raw_value(self, value: Any) -> str:
        """Convert value of `field_datatype` to a raw string value.
        This function typically calls on field set.

        Checks incoming value against `field_datatype`, validates it
        using `validation_cb` (if any) and converts it using `set_cb`
        (if any).

        Args:
            value (Any): value of `field_datatype`

        Returns:
            str: raw value string representation

        """
        if not isinstance(value, self._field_datatype):
            raise TypeError(f"Bad value type {type(value)}, must be {self._field_datatype}")

        if not (self._validation_cb is None or self._validation_cb(value)):
            raise ValueError(f"Value {value} does not meet to field restrictions")

        if isinstance(value, Enum):
            value = value.value

        if self._set_cb is not None:
            value = self._set_cb(value)

        return str(value)

    def to_field_value(self, value: str) -> Optional[_FieldDataT]:
        """Convert raw string value to a value of `field_datatype`.
        This function typically calls on field get.

        Converts incoming value using `get_cb` (if any). If
        type of value after that is not an instance of `field_datatype`,
        then tries to cast value to `field_datatype` (if specified).

        Args:
            value (str): raw string representation

        Returns:
            Optional[_FieldDataT]: value of `field_datatype`

        """
        new_value = value
        if self._get_cb is not None:
            new_value = self._get_cb(value)
        if not isinstance(new_value, self._field_datatype) and new_value is not None:
            return self._field_datatype(new_value)  # type: ignore

        return new_value

    def __hash__(self) -> int:
        return hash(self._raw_name)

    def __get__(self, instance: Optional["Model"], _: Any) -> Optional[_FieldDataT]:
        """Model field getter. It does the following:

        1. Retrieve raw field value of `raw_name`. If nothing then
           just return None
        2. If `get_cb` is set then call it and use its result as value
        3. If value is not instance of `field_datatype` then try to
           cast it to this type
        4. Return value as field value

        """
        if instance is None:
            return self  # type: ignore

        value: Optional[str] = instance._raw_data.get(self._raw_name)
        if value is not None:
            return self.to_field_value(value)

        return value

    def __set__(self, instance: Optional["Model"], value: Any) -> None:
        """Model field setter. If value is set to None, then raw value
        is marked "removed" and the instance is marked dirty.

        Otherwise it does the following:

        1. Check if value has `field_datatype` type, raise an error
           if not
        2. If `validation_cb` is set then call it, if result is false
           then raise an error
        3. Extract Enum value if value is Enum
        4. If `set_cb` is set then call it and use its result as value
        5. Write `str(value)` to raw field value of `raw_name`
        6. Mark instance as dirty
        """
        if instance is None:
            return

        if value is None:
            self.__delete__(instance)
            return

        raw_value = self.to_raw_value(value)
        instance._raw_data[self._raw_name] = raw_value  # noqa
        instance._dirty = True

    def __delete__(self, instance: Optional["Model"]) -> None:
        if instance is None:
            return

        if self._raw_name in instance._raw_data:
            del instance._raw_data[self._raw_name]
            instance._dirty = True


class ModelMeta(type):
    def __new__(mcs: Type["ModelMeta"], name: str, bases: tuple, attrs: dict) -> Any:
        attrs["_fields_mapping"] = {}
        attrs.setdefault("__annotations__", {})  # python >= 3.6
        for attr_name, attr in attrs.items():
            if isinstance(attr, Field):
                attrs["_fields_mapping"][attr_name] = attr.raw_name
                # Set field doc and annotations to correct render field
                # in documentation
                attrs[attr_name].__doc__ = f"{name}.{attr_name}"
                attrs["__annotations__"][attr_name] = attr.field_datatype

        klass = super(ModelMeta, mcs).__new__(mcs, name, bases, attrs)
        models_registry[name] = cast(Type["Model"], klass)
        return klass


_ModelT = TypeVar("_ModelT", bound="Model")


class Model(metaclass=ModelMeta):
    """Model base class. Derived classes must define fields and set table_name.

    Model has a "dirty" flag inside. Dirty instance means that it has the changes
    that are not saved to the device. The opposite is "clean" instance.
    """

    table_name: ClassVar[str]
    """Raw table name on device"""

    _fields_mapping: ClassVar[Mapping[str, str]]

    def __init__(self, **fields: Any) -> None:
        """Accepts initial fields data in kwargs"""
        self._sdk: Optional["ZKSDK"] = None
        self._dirty = True
        self._raw_data: MutableMapping[str, str] = {}

        assert self._fields_mapping is not None, f"No fields mapping in model {self.__class__.__name__}"
        fm = self._fields_mapping
        if fields:
            unknown_fields = fields.keys() - fm.keys()
            if unknown_fields:
                raise TypeError(f"Unknown fields: {tuple(unknown_fields)}")

            self._raw_data = {
                fm[field]: getattr(self.__class__, field).to_raw_value(fields.get(field))
                for field in fm.keys() & fields.keys()
                if fields.get(field) is not None
            }

    @property
    def dict(self) -> Dict[str, _FieldDataT]:
        return {field: getattr(self, field) for field in self._fields_mapping.keys()}

    @property
    def raw_data(self) -> Dict[str, str]:
        """Return the raw data that we read from or write to a device"""
        return {field: self._raw_data.get(field, "") for field in self._fields_mapping.values()}

    @classmethod
    def fields_mapping(cls) -> Mapping[str, str]:
        """Mapping between model fields and their raw fields"""
        return cls._fields_mapping

    def delete(self) -> None:
        """Delete this record from a table. Marks an instance as "dirty"."""
        if self._sdk is None:
            raise TypeError("Unable to delete a manually created data table record")

        gen = self._sdk.delete_device_data(self.table_name)
        gen.send(None)
        gen.send(self.raw_data)
        try:
            gen.send(None)
        except StopIteration:
            pass

        self._dirty = True

    def save(self) -> None:
        """Save changes in this record. Marks an instance as "clean"."""
        if self._sdk is None:
            raise TypeError("Unable to save a manually created data table record")

        gen = self._sdk.set_device_data(self.table_name)
        gen.send(None)
        gen.send(self.raw_data)
        try:
            gen.send(None)
        except StopIteration:
            pass

        self._dirty = False

    def with_raw_data(self: _ModelT, raw_data: MutableMapping[str, str], dirty: bool = True) -> _ModelT:
        self._raw_data = raw_data
        self._dirty = dirty
        return self

    def with_sdk(self: _ModelT, sdk: "ZKSDK") -> _ModelT:
        self._sdk = sdk
        return self

    def with_zk(self: _ModelT, zk: "ZKAccess") -> _ModelT:
        """Bind current object with ZKAccess connection

        Args:
            zk (ZKAccess): ZKAccess object

        Returns:
            Model: self

        """
        self._sdk = zk.sdk
        return self

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return self._raw_data == other._raw_data and self.table_name == other.table_name

    def __repr__(self) -> str:
        data = ", ".join(f"{f}={self.raw_data.get(k)}" for f, k in sorted(self.fields_mapping().items()))
        return f"{'*' if self._dirty else ''}{self.__class__.__name__}({data})"
