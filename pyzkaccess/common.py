__all__ = [
    'UserTuple',
    'DocValue',
    'DocDict'
]
from copy import copy, deepcopy
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
