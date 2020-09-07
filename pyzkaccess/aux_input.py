__all__ = [
    'AuxInput',
    'AuxInputList'
]
from abc import ABCMeta, abstractmethod
from typing import Iterable

from .common import UserTuple
from .event import EventLog
from .sdk import ZKSDK


class AuxInputInterface(metaclass=ABCMeta):
    event_types = (220, 221)

    @property
    def events(self) -> EventLog:
        """Event log of current aux input"""
        return self._specific_event_log()

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class AuxInput(AuxInputInterface):
    """Concrete auxiliary input"""
    def __init__(self, sdk: ZKSDK, event_log: EventLog, number: int):
        self.number = number
        self._sdk = sdk
        self._event_log = event_log

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[self.number], event_type=self.event_types)

    def __eq__(self, other):
        if isinstance(other, AuxInput):
            return self.number == other.number and self._sdk is other._sdk
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "AuxInput[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class AuxInputList(AuxInputInterface, UserTuple):
    """Collection of aux input objects which is used to perform group
    operations over multiple aux inputs
    """
    def __init__(self, sdk: ZKSDK, event_log: EventLog, aux_inputs: Iterable[AuxInput] = ()):
        super().__init__(aux_inputs)
        self._sdk = sdk
        self._event_log = event_log

    def __getitem__(self, item):
        aux_inputs = self.data[item]
        if isinstance(item, slice):
            return self.__class__(self._sdk, self._event_log, aux_inputs=aux_inputs)
        else:
            return aux_inputs

    def _specific_event_log(self) -> EventLog:
        doors = set(x.number for x in self)
        return self._event_log.only(door=doors, event_type=self.event_types)
