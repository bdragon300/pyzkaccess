from abc import ABCMeta, abstractmethod
from typing import Iterable, Union

from .common import UserTuple
from .event import EventLog
from .sdk import ZKSDK


class ReaderInterface(metaclass=ABCMeta):
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
        return self._event_log.only(door=[self.number])  # FIXME: event_types

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
        readers = super().__getitem__(item)
        if isinstance(item, slice):
            return self.__class__(self._sdk, self._event_log, readers=readers)
        else:
            return readers

    def _specific_event_log(self) -> EventLog:
        doors = [x.number for x in self]
        return self._event_log.only(door=doors)  # FIXME: event_types
