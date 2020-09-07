__all__ = [
    'Door',
    'DoorList'
]
from abc import ABCMeta, abstractmethod
from typing import Iterable, Union

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
        """Event log of current door. This includes events of its
        relays, readers, aux inputs and so forth
        """
        return self._specific_event_log()

    @property
    @abstractmethod
    def relays(self) -> RelayList:
        """Relays which belong to this door"""
        pass

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class Door(DoorInterface):
    """Concrete door"""
    def __init__(self,
                 sdk: ZKSDK,
                 event_log: EventLog,
                 number: int,
                 relays: RelayList,
                 reader: Reader,
                 aux_input: AuxInput,
                 parameters: DoorParameters):
        self.number = number
        self._sdk = sdk
        self._event_log = event_log
        self._relays = relays
        self._reader = reader
        self._aux_input = aux_input
        self._parameters = parameters

    @property
    def relays(self) -> RelayList:
        return self._relays

    @property
    def reader(self) -> Reader:
        """Reader which belong to this door"""
        return self._reader

    @property
    def aux_input(self) -> AuxInput:
        """Aux input which belong to this door"""
        return self._aux_input

    @property
    def parameters(self) -> DoorParameters:
        """Device parameters related to this door"""
        return self._parameters

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[self.number])

    def __eq__(self, other):
        if isinstance(other, Door):
            return self.number == other.number \
                   and self._sdk is other._sdk \
                   and self._relays == other._relays \
                   and self._reader == other._reader \
                   and self._aux_input == other._aux_input
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "Door[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class DoorList(DoorInterface, UserTuple):
    """Collection of door objects which is used to perform group
    operations over multiple doors
    """
    def __init__(self, sdk: ZKSDK, event_log: EventLog, doors: Iterable[Door]):
        super().__init__(doors)
        self._sdk = sdk
        self._event_log = event_log

    @property
    def relays(self) -> RelayList:
        """Relays which belong to this doors"""
        relays = [relay for door in self for relay in door.relays]
        return RelayList(self._sdk, relays=relays)

    @property
    def readers(self) -> ReaderList:
        """Readers which belong to this door"""
        readers = [x.reader for x in self]
        return ReaderList(self._sdk, event_log=self._event_log, readers=readers)

    @property
    def aux_inputs(self) -> AuxInputList:
        """Aux inputs which belong to this door"""
        aux_inputs = [x.aux_input for x in self]
        return AuxInputList(self._sdk, event_log=self._event_log, aux_inputs=aux_inputs)

    def __getitem__(self, item: Union[int, slice]) -> Union[Door, 'DoorList']:
        doors = self.data[item]
        if isinstance(item, slice):
            return self.__class__(self._sdk, self._event_log, doors=doors)
        else:
            return doors

    def _specific_event_log(self) -> EventLog:
        doors = set(x.number for x in self)
        return self._event_log.only(door=doors)
