from abc import ABCMeta, abstractmethod
from typing

class DoorInterface(metaclass=ABCMeta):
    @property
    def events(self) -> EventLog:
        return self._specific_event_log()

    def poll(self, timeout: int = 60) -> Iterable[Event]:
        return self._specific_event_log().poll(timeout)

    @abstractmethod
    def _specific_event_log(self) -> EventLog:
        pass