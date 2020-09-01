from typing import Sequence, Union, Iterable
from copy import copy


class UserTuple:
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
    def __lt__(self, other): return self.data <  self.__cast(other)
    def __le__(self, other): return self.data <= self.__cast(other)
    def __eq__(self, other): return self.data == self.__cast(other)
    def __gt__(self, other): return self.data >  self.__cast(other)
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
