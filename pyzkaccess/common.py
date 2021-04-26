__all__ = [
    'UserTuple',
    'DocValue',
    'DocDict',
    'ZKDatetimeUtils'
]
from copy import copy, deepcopy
from datetime import datetime, time, date
from typing import Sequence, Union, Iterable

from wrapt import ObjectProxy
from wrapt.wrappers import _ObjectProxyMetaType  # noqa


class UserTuple:
    """Immutable version of `collections.UserList` from the stdlib"""
    def __init__(self, initlist: Union[Sequence, Iterable, 'UserTuple'] = None):
        self.data = tuple()
        if initlist is not None:
            # XXX should this accept an arbitrary sequence?
            if isinstance(initlist, tuple):
                self.data = initlist
            elif isinstance(initlist, UserTuple):
                self.data = copy(initlist.data)
            else:
                self.data = tuple(initlist)

    def __repr__(self): return repr(self.data)
    def __lt__(self, other): return self.data <  self.__cast(other)  # noqa
    def __le__(self, other): return self.data <= self.__cast(other)
    def __eq__(self, other): return self.data == self.__cast(other)
    def __gt__(self, other): return self.data >  self.__cast(other)  # noqa
    def __ge__(self, other): return self.data >= self.__cast(other)

    def __cast(self, other):
        return other.data if isinstance(other, UserTuple) else other

    def __contains__(self, item): return item in self.data
    def __len__(self): return len(self.data)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__class__(self.data[i])
        else:
            return self.data[i]

    def __add__(self, other):
        if isinstance(other, UserTuple):
            return self.__class__(self.data + other.data)
        elif isinstance(other, type(self.data)):
            return self.__class__(self.data + other)
        return self.__class__(self.data + list(other))

    def __radd__(self, other):
        if isinstance(other, UserTuple):
            return self.__class__(other.data + self.data)
        elif isinstance(other, type(self.data)):
            return self.__class__(other + self.data)
        return self.__class__(list(other) + self.data)

    def __iadd__(self, other):
        if isinstance(other, UserTuple):
            self.data += other.data
        elif isinstance(other, type(self.data)):
            self.data += other
        else:
            self.data += list(other)
        return self

    def __mul__(self, n):
        return self.__class__(self.data*n)

    __rmul__ = __mul__

    def __imul__(self, n):
        self.data *= n
        return self

    def __hash__(self):
        return hash(self.data)

    def __copy__(self):
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        # Create a copy and avoid triggering descriptors
        inst.__dict__["data"] = self.__dict__["data"][:]
        return inst

    def copy(self): return self.__class__(self)
    def count(self, item): return self.data.count(item)
    def index(self, item, *args): return self.data.index(item, *args)


class DocValueMeta(_ObjectProxyMetaType):
    def __new__(cls, name, bases, attrs):
        # Hack: override class creation for proxy object since
        # ObjectProxy metaclass doesn't allow easily redefine __doc__
        def get_doc(self):
            return self._self_doc if self._self_doc else self.__wrapped__.__doc__

        doc_prop = property(get_doc, None, None)

        new_class = super().__new__(cls, name, bases, attrs)
        type.__setattr__(new_class, '__doc__', doc_prop)
        type.__setattr__(new_class, '__module__', '')
        return new_class


class DocValue(ObjectProxy, metaclass=DocValueMeta):
    """Value of type with custom __doc__ attribute. The main aim is to
    annotate a value of any type including built-in ones
    """
    def __init__(self, value: Union[str, int], doc: str):
        """
        :param value: value which was exposed by this object
        :param doc: documentation string which will be put to __doc__
        """
        super().__init__(value)
        if not isinstance(value, (str, int)):
            raise TypeError('Init value type must be int or str')

        self._self_value = value
        self._self_doc = doc

    def __repr__(self):
        return self.__wrapped__.__repr__()

    @property
    def value(self):
        """Exposed value"""
        return self._self_value

    @property
    def doc(self):
        """Documentation of a value"""
        return self._self_doc

    def __copy__(self):
        obj = DocValue(copy(self._self_value), copy(self._self_doc))
        return obj

    def __deepcopy__(self, memodict=None):
        obj = DocValue(deepcopy(self._self_value), deepcopy(self._self_doc))
        return obj


class DocDict(dict):
    """DocDict is dictionary, where values are annotated versions
    of keys.

    As initial value DocDict accepts a dictionary where dict key is
    an exposed value and dict value is docstring.

        >>> d = DocDict({1: 'Docstring 1', '2': 'Docstring 2'})
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
    def __init__(self, initdict: dict):
        super().__init__({k: DocValue(k, v) for k, v in initdict.items()})


class ZKDatetimeUtils:
    """
    Utility functions to work with date/time types in ZKAccess SDK.

    ZK devices has various ways to work with dates and time. In
    order to make working with dates more convenient in user's code,
    these functions converts standard python objects from datetime
    module into a specific format.
    """
    @staticmethod
    def zkctime_to_datetime(zkctime: Union[str, int]) -> datetime:
        """Convert ZK-specific ctime integer value to a datetime object.

        Simply put this ctime is a count of seconds starting from
        `2000-01-01 00:00:00` without considering leap years/seconds
        and days count in months (always 31 day)
        :param zkctime: ZK ctime integer or string value
        :return: datetime object
        """
        if isinstance(zkctime, str):
            zkctime = int(zkctime)

        if zkctime < 0:
            raise ValueError('Value must be a positive number')

        return datetime(
            year=zkctime // 32140800 + 2000,
            month=(zkctime // 2678400) % 12 + 1,
            day=(zkctime // 86400) % 31 + 1,
            hour=(zkctime // 3600) % 24,
            minute=(zkctime // 60) % 60,
            second=zkctime % 60
        )

    @staticmethod
    def datetime_to_zkctime(dt: datetime) -> int:
        """Converts datetime object to a ZK-specific ctime value.
        Such type can be found in device parameters and data tables.

        Simply put this ctime is a count of seconds starting from
        `2000-01-01 00:00:00` without considering leap years/seconds
        and days count in months (always 31 day)
        :param dt: datetime object
        :return: ZK ctime integer value
        """
        if dt.year < 2000:
            raise ValueError('Cannot get zkctime from a date earlier than a midnight of 2000-01-01')

        return sum((
            sum((
                (dt.year - 2000) * 12 * 31,
                (dt.month - 1) * 31,
                (dt.day - 1)
            )) * 24 * 60 * 60,
            dt.hour * 60 * 60,
            dt.minute * 60,
            dt.second
        ))

    @staticmethod
    def time_string_to_datetime(dt_string: str) -> datetime:
        """Parses datetime string and return datetime object. Such value
        is used in events list. Datetime string has ISO date format.
        :param dt_string: datetime string such as `2021-04-15 21:21:00`
        :return: datetime object
        """
        return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')

    @staticmethod
    def zktimerange_to_times(zktr: Union[str, int]) -> (time, time):
        """Decode 4-byte time range into time objects couple.
        Such approach is used in Timezone table.

        Simply put, the higher 2 bytes are "from" part of range,
        the lower 2 bytes are "to" part. Time part is encoded as
        `(hour * 100) + minutes`.
        :param zktr: encoded time range as integer or as number in string
        :return: time objects from-to couple (without timezone)
        """
        if isinstance(zktr, str):
            zktr = int(zktr)

        if zktr < 0:
            raise ValueError('time range cannot be a negative number')

        to_num = zktr & 0xffff
        from_num = (zktr >> 16) & 0xffff
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
        :param from_t: time/datetime "from" part of time range
        :param to_t: time/datetime "to" part of time range
        :return: encoded 4-byte integer
        """
        return ((from_t.hour * 100 + from_t.minute) << 16) + (to_t.hour * 100 + to_t.minute)

    @staticmethod
    def zkdate_to_date(zkd: str) -> date:
        """Parse date string and return date object. Such format is
        used in User table.

        Date format is simple: 'YYYYMMDD'
        :param zkd: date string
        :return: parsed date object
        """
        return datetime.strptime(zkd, '%Y%m%d').date()

    @staticmethod
    def date_to_zkdate(d: Union[date, datetime]) -> str:
        """Make a date string from a given date/datetime object. Such
        format is used in User table.

        Date format is simple: 'YYYYMMDD'
        :param d: date/datetime object
        :return: date string
        """
        return d.strftime('%Y%m%d')
