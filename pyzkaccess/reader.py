from abc import ABCMeta, abstractmethod
from typing import Iterable

from .common import UserTuple
from .event import EventLog
from .sdk import ZKSDK


class ReaderInterface(metaclass=ABCMeta):
    @property
    def events(self) -> EventLog:
        return self._specific_event_log()

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class Reader(ReaderInterface):
    def __init__(self, sdk: ZKSDK, event_log: EventLog, number: int):
        self.sdk = sdk
        self._event_log = event_log
        self.number = number

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[str(self.number)])  # FIXME: event_types

    def __str__(self):
        return "Reader[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class ReaderList(ReaderInterface, UserTuple):
    def __init__(self, sdk: ZKSDK, event_log: EventLog, readers: Iterable[Reader] = ()):
        super().__init__(readers)
        self.sdk = sdk
        self._event_log = event_log

    def __getitem__(self, item):
        readers = super().__getitem__(item)
        if isinstance(item, slice):
            return self.__class__(self.sdk, self._event_log, readers=readers)
        else:
            return readers

    def _specific_event_log(self) -> EventLog:
        doors = [str(x.number) for x in self]
        return self._event_log.only(door=doors)  # FIXME: event_types
