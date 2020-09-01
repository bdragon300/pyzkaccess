from abc import ABCMeta, abstractmethod
from typing import Iterable

from .common import UserTuple
from .event import EventLog
from .reader import ReaderList, Reader
from .relay import RelayList
from .sdk import ZKSDK


class DoorInterface(metaclass=ABCMeta):
    @property
    def events(self) -> EventLog:
        return self._specific_event_log()

    @property
    @abstractmethod
    def relays(self) -> RelayList:
        pass

    # TODO: aux inputs

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class Door(DoorInterface):
    def __init__(self,
                 sdk: ZKSDK,
                 event_log: EventLog,
                 number: int,
                 relays: RelayList,
                 reader: Reader):
        self.sdk = sdk
        self.number = number
        self._event_log = event_log
        self._relays = relays
        self._reader = reader

    @property
    def relays(self) -> RelayList:
        return self._relays

    @property
    def reader(self):
        return self._reader

    def _specific_event_log(self) -> EventLog:
        return self._event_log.include(door=[str(self.number)])

    def __str__(self):
        return "Door[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class DoorList(DoorInterface, UserTuple):
    def __init__(self, sdk: ZKSDK, event_log: EventLog, doors: Iterable[Door]):
        super().__init__(doors)
        self.sdk = sdk
        self._event_log = event_log

    @property
    def relays(self) -> RelayList:
        relays = [relay for door in self for relay in door.relays]
        return RelayList(self.sdk, relays=relays)

    @property
    def readers(self):
        readers = [x.reader for x in self]
        return ReaderList(self.sdk, event_log=self._event_log, readers=readers)

    def __getitem__(self, item):
        doors = super().__getitem__(item)
        if isinstance(item, slice):
            return self.__class__(self.sdk, self._event_log, doors=doors)
        else:
            return doors

    def _specific_event_log(self) -> EventLog:
        doors = [str(x.number) for x in self]
        return self._event_log.include(door=doors)
