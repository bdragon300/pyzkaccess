__all__ = [
    'Reader',
    'ReaderList'
]
from abc import ABCMeta, abstractmethod
from typing import Iterable, Union

from .common import UserTuple
from .event import EventLog
from .sdk import ZKSDK


class ReaderInterface(metaclass=ABCMeta):
    #: Event types which are fully or partially related to a reader
    #: See EVENT_TYPES enum and SDK docs
    event_types = frozenset((0, 1, 2, 3, 4, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 26,
                             27, 29, 30, 31, 32, 33, 34, 35, 36, 101, 103, 203))

    @property
    def events(self) -> EventLog:
        """Event log of current reader"""
        return self._specific_event_log()

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class Reader(ReaderInterface):
    """Concrete reader"""
    def __init__(self, sdk: ZKSDK, event_log: EventLog, number: int):
        self.number = number
        self._sdk = sdk
        self._event_log = event_log

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[self.number], event_type=self.event_types)

    def __eq__(self, other):
        if isinstance(other, Reader):
            return self.number == other.number and self._sdk is other._sdk
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "Reader[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class ReaderList(ReaderInterface, UserTuple):
    """Collection of reader objects which is used to perform group
    operations over multiple readers
    """
    def __init__(self, sdk: ZKSDK, event_log: EventLog, readers: Iterable[Reader] = ()):
        super().__init__(readers)
        self._sdk = sdk
        self._event_log = event_log

    def __getitem__(self, item: Union[int, slice]) -> Union[Reader, 'ReaderList']:
        readers = self.data[item]
        if isinstance(item, slice):
            return self.__class__(self._sdk, self._event_log, readers=readers)
        else:
            return readers

    def _specific_event_log(self) -> EventLog:
        doors = set(x.number for x in self)
        return self._event_log.only(door=doors, event_type=self.event_types)
