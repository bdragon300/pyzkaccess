__all__ = ["AuxInput", "AuxInputList"]
from abc import ABCMeta, abstractmethod
from typing import Any, Iterable, TypeVar, Union, overload

from pyzkaccess.common import UserTuple
from pyzkaccess.event import EventLog
from pyzkaccess.sdk import ZKSDK


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
    """An auxiliary input"""

    def __init__(self, sdk: ZKSDK, event_log: EventLog, number: int):
        self.number = number
        self._sdk = sdk
        self._event_log = event_log

    def _specific_event_log(self) -> EventLog:
        return self._event_log.only(door=[self.number], event_type=self.event_types)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AuxInput):
            return self.number == other.number and self._sdk is other._sdk
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f"AuxInput[{self.number}]"

    def __repr__(self) -> str:
        return self.__str__()


_AuxInputListT = TypeVar("_AuxInputListT", bound="AuxInputList")


class AuxInputList(AuxInputInterface, UserTuple[AuxInput]):
    """Auxiliary input collection for group operations"""

    def __init__(self, sdk: ZKSDK, event_log: EventLog, aux_inputs: Iterable[AuxInput] = ()):
        super().__init__(aux_inputs)
        self._sdk = sdk
        self._event_log = event_log

    @overload
    def __getitem__(self, item: int) -> AuxInput:
        pass

    @overload
    def __getitem__(self: _AuxInputListT, item: slice) -> _AuxInputListT:
        pass

    def __getitem__(self: _AuxInputListT, item: Union[int, slice]) -> Union[AuxInput, _AuxInputListT]:
        if isinstance(item, slice):
            return self.__class__(self._sdk, self._event_log, aux_inputs=self.data[item])

        return self.data[item]

    def _specific_event_log(self) -> EventLog:
        doors = set(x.number for x in self)
        return self._event_log.only(door=doors, event_type=self.event_types)
