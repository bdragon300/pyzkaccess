from typing import Iterable

from .sdk import ZKSDK
from .event import EventLog


class Reader:
    def __init__(self, sdk: ZKSDK, event_log: EventLog, number: int):
        self.sdk = sdk
        self.event_log = event_log
        self.number = number

    def poll(self, timeout: int = 60):
        return self.event_log.include(door=[str(self.number)]).poll(timeout)

    def __str__(self):
        return "Reader[{}]".format(self.number)

    def __repr__(self):
        return self.__str__()


class ReaderList(list):
    def __init__(self, sdk: ZKSDK, event_log: EventLog, readers: Iterable[Reader] = ()):
        super().__init__(readers)
        self.sdk = sdk
        self.event_log = event_log

    def __getitem__(self, item):
        readers = super().__getitem__(item)
        if isinstance(item, slice):
            return self.__class__(self.sdk, self.event_log, readers=readers)
        else:
            return readers

    def poll(self, timeout: int = 60):
        doors = [str(x.number) for x in self]
        return self.event_log.include(door=doors).poll(timeout)