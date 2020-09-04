from abc import ABCMeta, abstractmethod
from typing import Iterable

from .common import UserTuple
from .event import EventLog
from .sdk import ZKSDK


class AuxInputInterface(metaclass=ABCMeta):
    event_types = (220, 221)

    @property
    def events(self) -> EventLog:
        return self._specific_event_log()

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass


class AuxInput(AuxInputInterface):
    def __init__(self, sdk: ZKSDK, event_log: EventLog, number: int):
        self.sdk = sdk
        self.number = number
        self._event_log = event_log

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[self.number], event_type=self.event_types)

    def __str__(self):
        return "AuxInput[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class AuxInputList(AuxInputInterface, UserTuple):
    def __init__(self, sdk: ZKSDK, event_log: EventLog, aux_inputs: Iterable[AuxInput] = ()):
        super().__init__(aux_inputs)
        self.sdk = sdk
        self._event_log = event_log

    def __getitem__(self, item):
        aux_inputs = super().__getitem__(item)
        if isinstance(item, slice):
            return self.__class__(self.sdk, self._event_log, aux_inputs=aux_inputs)
        else:
            return aux_inputs

    def _specific_event_log(self) -> EventLog:
        doors = [x.number for x in self]
        return self._event_log.only(door=doors, event_type=self.event_types)
