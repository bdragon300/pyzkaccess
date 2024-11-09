__all__ = ["UserTuple", "DocValue", "DocDict", "ZKDatetimeUtils"]
from copy import copy, deepcopy
from datetime import date, datetime, time
from typing import Any, Generic, Iterable, Mapping, Optional, Sequence, Tuple, Type, TypeVar, Union, overload

from wrapt import ObjectProxy
from wrapt.wrappers import _ObjectProxyMetaType  # noqa; pylint: disable=import-private-name

_DataT = TypeVar("_DataT")
_UserTupleT = TypeVar("_UserTupleT", bound="UserTuple")


class UserTuple(Sequence[_DataT]):
    """Immutable version of `collections.UserList` from the stdlib"""

    def __init__(self, initlist: Union[Iterable[_DataT], "UserTuple[_DataT]"] = ()):
        self._data: Tuple[_DataT, ...]
        if isinstance(initlist, tuple):
            self._data = initlist
        elif isinstance(initlist, UserTuple):
            self._data = copy(initlist._data)
        else:
            self._data = tuple(initlist)

    @property
    def data(self) -> Tuple[_DataT, ...]:
        return self._data

    @data.setter
    def data(self, value: Iterable[_DataT]) -> None:
        self._data = tuple(value)

    def __repr__(self) -> str:
        return repr(self._data)

    def __lt__(self, other: Any) -> bool:
        return self._data < self.__cast(other)  # noqa

    def __le__(self, other: Any) -> bool:
        return self._data <= self.__cast(other)

    def __eq__(self, other: Any) -> bool:
        return self._data == self.__cast(other)

    def __gt__(self, other: Any) -> bool:
        return self._data > self.__cast(other)  # noqa

    def __ge__(self, other: Any) -> bool:
        return self._data >= self.__cast(other)

    @staticmethod
    def __cast(other: Any) -> Any:
        return other._data if isinstance(other, UserTuple) else other  # pylint: disable=protected-access

    def __contains__(self, item: Any) -> bool:
        return item in self._data

    def __len__(self) -> int:
        return len(self._data)

    @overload
    def __getitem__(self, i: int) -> _DataT: ...

    @overload
    def __getitem__(self: _UserTupleT, i: slice) -> _UserTupleT: ...

    def __getitem__(self: _UserTupleT, i: Union[int, slice]) -> Union[_DataT, _UserTupleT]:
        if isinstance(i, slice):
            return self.__class__(self._data[i])

        return self._data[i]

    def __add__(self: _UserTupleT, other: Iterable[_DataT]) -> _UserTupleT:
        if isinstance(other, UserTuple):
            return self.__class__(self._data + other._data)
        return self.__class__(self._data + tuple(other))

    def __radd__(self: _UserTupleT, other: Iterable[_DataT]) -> _UserTupleT:
        if isinstance(other, UserTuple):
            return self.__class__(other._data + self._data)
        return self.__class__(tuple(other) + self._data)

    def __iadd__(self: _UserTupleT, other: Iterable[_DataT]) -> _UserTupleT:
        if isinstance(other, UserTuple):
            self._data += other._data
        else:
            self._data += tuple(other)
        return self

    def __mul__(self: _UserTupleT, n: int) -> _UserTupleT:
        return self.__class__(self._data * n)

    __rmul__ = __mul__

    def __imul__(self: _UserTupleT, n: int) -> _UserTupleT:
        self._data *= n
        return self

    def __hash__(self) -> int:
        return hash(self._data)

    def __copy__(self: _UserTupleT) -> _UserTupleT:
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        # Create a copy and avoid triggering descriptors
        inst.__dict__["_data"] = self.__dict__["_data"][:]
        return inst

    def copy(self: _UserTupleT) -> _UserTupleT:
        return self.__class__(self)

    def count(self, value: _DataT) -> int:
        return self._data.count(value)

    def index(self, value: _DataT, *args: Any, **kwargs: Any) -> int:
        return self._data.index(value, *args, **kwargs)


_DocValueValueT = TypeVar("_DocValueValueT", bound=Union[str, int])
_DocValueT = TypeVar("_DocValueT", bound="DocValue")


class DocValueMeta(_ObjectProxyMetaType):
    def __new__(mcs, name: str, bases: tuple, attrs: dict) -> Any:
        # Hack: override class creation for proxy object since
        # ObjectProxy metaclass doesn't allow easily redefine __doc__
        def get_doc(self: _DocValueT) -> str:
            return self._self_doc if self._self_doc else self.__wrapped__.__doc__  # pylint: disable=protected-access

        doc_prop = property(get_doc, None, None)

        new_class = super().__new__(mcs, name, bases, attrs)  # pylint: disable=too-many-function-args
        type.__setattr__(new_class, "__doc__", doc_prop)
        type.__setattr__(new_class, "__module__", "")
        return new_class


class DocValue(ObjectProxy, Generic[_DocValueValueT], metaclass=DocValueMeta):
    """Value of type with custom __doc__ attribute. The main aim is to
    annotate a value of any type including built-in ones
    """

    def __init__(self, value: _DocValueValueT, doc: str) -> None:
        """DocValue constructor

        Args:
            value (_DocValueValueT): value which was exposed by this object
            doc (str): documentation string which will be put to __doc__
        """
        super().__init__(value)
        if not isinstance(value, (str, int)):
            raise TypeError("Init value type must be int or str")

        self._self_value = value
        self._self_doc = doc

    def __repr__(self) -> str:
        return self.__wrapped__.__repr__()

    @property
    def value(self) -> _DocValueValueT:
        """Exposed value"""
        return self._self_value

    @property
    def doc(self) -> str:
        """Documentation of a value"""
        return self._self_doc

    def __copy__(self: _DocValueT) -> _DocValueT:
        obj = DocValue(copy(self._self_value), copy(self._self_doc))
        return obj

    def __deepcopy__(self: _DocValueT, memodict: Optional[dict] = None) -> _DocValueT:
        obj = DocValue(deepcopy(self._self_value), deepcopy(self._self_doc))
        return obj

    def __reduce__(self: _DocValueT) -> Tuple[Type[_DocValueT], Tuple[_DocValueValueT, str]]:
        return type(self), (self._self_value, self._self_doc)

    def __reduce_ex__(self: _DocValueT, _: Any) -> Tuple[Type[_DocValueT], Tuple[_DocValueValueT, str]]:
        return self.__reduce__()


class DocDict(dict, Generic[_DocValueValueT]):
    """DocDict is dictionary, where values are annotated versions
    of keys.

    As initial value DocDict accepts a dictionary where dict key is
    an exposed value and dict value is docstring.

        >>> d = DocDict[int, str]({1: 'Docstring 1', '2': 'Docstring 2'})
        >>> print(repr(d[1]), repr(d['2']))
        1 '2'
        >>> print(type(d[1]), type(d['2']))
        <class 'DocValue'> <class 'DocValue'>
        >>> print(d[1] == 1)
        True
        >>> print(d['2'] == '2')
        True
        >>> print(isinstance(d[1], int), isinstance(d['2'], str))
        True True
        >>> print(d[1].__doc__, ',', d['2'].__doc__)
        Docstring 1 , Docstring 2
    """

    def __init__(self, initdict: Mapping[_DocValueValueT, str]) -> None:
        super().__init__({k: DocValue[_DocValueValueT](k, v) for k, v in initdict.items()})


class ZKDatetimeUtils:
    """Utility functions to work with datetimes in ZKAccess SDK.

    ZK device developers reinvented the wheel and used their own
    weird datetime representation in some tables and parameters.
    Moreover, they used completely different formats in different
    places.

    God only knows why they didn't use the ISO datetime or timestamps
    or something like that.

    This class provides the methods to convert such values to standard
    Python datetime objects and vice versa.
    """

    @staticmethod
    def zkctime_to_datetime(zkctime: Union[str, int]) -> datetime:
        """Convert ZK-specific ctime integer value to a datetime object.

        Simply put this ctime is a count of seconds starting from
        `2000-01-01 00:00:00` without considering leap years/seconds
        and days count in months (always 31 day)

        Args:
            zkctime (Union[str, int]): ZK ctime integer or string value

        Returns:
            datetime: converted datetime

        """
        if isinstance(zkctime, str):
            zkctime = int(zkctime)

        if zkctime < 0:
            raise ValueError("Value must be a positive number")

        return datetime(
            year=zkctime // 32140800 + 2000,
            month=(zkctime // 2678400) % 12 + 1,
            day=(zkctime // 86400) % 31 + 1,
            hour=(zkctime // 3600) % 24,
            minute=(zkctime // 60) % 60,
            second=zkctime % 60,
        )

    @staticmethod
    def datetime_to_zkctime(dt: datetime) -> int:
        """Converts datetime object to a ZK-specific ctime value.
        Such type can be found in device parameters and data tables.

        Simply put this ctime is a count of seconds starting from
        `2000-01-01 00:00:00` without considering leap years/seconds
        and days count in months (always 31 day)

        Args:
            dt (datetime): datetime object to convert

        Returns:
            int: ZK ctime integer value

        """
        if dt.year < 2000:
            raise ValueError("Cannot get zkctime from a date earlier than a midnight of 2000-01-01")

        return sum(
            (
                sum(((dt.year - 2000) * 12 * 31, (dt.month - 1) * 31, (dt.day - 1))) * 24 * 60 * 60,
                dt.hour * 60 * 60,
                dt.minute * 60,
                dt.second,
            )
        )

    @staticmethod
    def time_string_to_datetime(dt_string: str) -> datetime:
        """Parses datetime string and return datetime object. Such value
        is used in events list. Datetime string has ISO date format.

        Args:
            dt_string (str): datetime string, e.g. `2021-04-15 21:21:00`

        Returns:
            datetime: converted datetime object

        """
        return datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def zktimerange_to_times(zktr: Union[str, int]) -> Tuple[time, time]:
        """Decode 4-byte time range into time objects couple.
        Such approach is used in Timezone table.

        Simply put, the higher 2 bytes are "from" part of range,
        the lower 2 bytes are "to" part. Time part is encoded as
        `(hour * 100) + minutes`.

        Args:
            zktr (Union[str, int]): encoded time range as integer or
                as number in string

        Returns:
            Tuple[time, time]: 2-tuple of from-tp time objects
                (without timezone)

        """
        if isinstance(zktr, str):
            zktr = int(zktr)

        if zktr < 0:
            raise ValueError("time range cannot be a negative number")

        to_num = zktr & 0xFFFF
        from_num = (zktr >> 16) & 0xFFFF
        from_t = time(hour=from_num // 100, minute=from_num % 100)
        to_t = time(hour=to_num // 100, minute=to_num % 100)

        return from_t, to_t

    @staticmethod
    def times_to_zktimerange(from_t: Union[datetime, time], to_t: Union[datetime, time]) -> int:
        """Encode time range in time/datetime objects into one 4-byte
        integer. Such approach is used in Timezone table.

        Simply put, the higher 2 bytes are "from" part of range,
        the lower 2 bytes are "to" part. Time part is encoded as
        `(hour * 100) + minutes`.

        Args:
            from_t (Union[datetime, time]): time/datetime "from" part
                of time range
            to_t (Union[datetime, time]): time/datetime "to" part
                of time range

        Returns:
            int: encoded 4-byte integer

        """
        return ((from_t.hour * 100 + from_t.minute) << 16) + (to_t.hour * 100 + to_t.minute)

    @staticmethod
    def zkdate_to_date(zkd: str) -> Optional[date]:
        """Parse date string and return date object. Such format is
        used in User table.

        Date format is simple: 'YYYYMMDD'

        Args:
            zkd (str): date string

        Returns:
            Optional[date]: parsed date object

        """
        # Device can return '0' string for date fields
        if zkd == "0":
            return None

        return datetime.strptime(zkd, "%Y%m%d").date()

    @staticmethod
    def date_to_zkdate(d: Union[date, datetime]) -> str:
        """Make a date string from a given date/datetime object. Such
        format is used in User table.

        Date format is simple: 'YYYYMMDD'

        Args:
            d (Union[date, datetime]): date/datetime object

        Returns:
            str: date string

        """
        return d.strftime("%Y%m%d")

    @staticmethod
    def zktimemoment_to_datetime(zktm: Union[str, int]) -> Optional[datetime]:
        """Decode 4-byte time annual time moment to a datetime with
        year and timezone ignored. Such approach is used in
        DaylightSavingTime, StandardTime parameters.

        Simply put, each byte represents time piece in order: month,
        day, hour, minute

        Args:
            zktm: (Union[str, int]): encoded annual time moment as
                integer or as number in string

        Returns:
            Optional[datetime]: decoded datetime object
        """
        if zktm in ("0", 0):
            return None

        if isinstance(zktm, str):
            zktm = int(zktm)

        return datetime(
            year=1970, month=(zktm >> 24) & 0xFF, day=(zktm >> 16) & 0xFF, hour=(zktm >> 8) & 0xFF, minute=zktm & 0xFF
        )

    @staticmethod
    def datetime_to_zktimemoment(dt: datetime) -> int:
        """Encode time moment in datetime object into a 4-byte integer
        used in a device as annual time moment representation. Year and
        timezone will be ignored. Such approach is used in
        DaylightSavingTime, StandardTime parameters.

        Args:
            dt: datetime object

        Returns:
            int: encoded annual time moment
        """
        return int((dt.month << 24) | (dt.day << 16) | (dt.hour << 8) | dt.minute)
