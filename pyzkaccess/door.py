from abc import ABCMeta, abstractmethod
from typing import Iterable

from .aux_input import AuxInput, AuxInputList
from .common import UserTuple
from .event import EventLog
from .param import DoorParameters
from .reader import Reader, ReaderList
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

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class Door(DoorInterface):
    def __init__(self,
                 sdk: ZKSDK,
                 event_log: EventLog,
                 number: int,
                 relays: RelayList,
                 reader: Reader,
                 aux_input: AuxInput,
                 parameters: DoorParameters):
        self.sdk = sdk
        self.number = number
        self._event_log = event_log
        self._relays = relays
        self._reader = reader
        self._aux_input = aux_input
        self._parameters = parameters

    @property
    def relays(self) -> RelayList:
        return self._relays

    @property
    def reader(self):
        return self._reader

    @property
    def aux_input(self):
        return self._aux_input

    @property
    def parameters(self):
        return self._parameters

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[self.number])

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

    @property
    def aux_inputs(self):
        aux_inputs = [x.aux_input for x in self]
        return AuxInputList(self.sdk, event_log=self._event_log, aux_inputs=aux_inputs)

    def __getitem__(self, item):
        doors = super().__getitem__(item)
        if isinstance(item, slice):
            return self.__class__(self.sdk, self._event_log, doors=doors)
        else:
            return doors

    def _specific_event_log(self) -> EventLog:
        doors = [x.number for x in self]
        return self._event_log.only(door=doors)
