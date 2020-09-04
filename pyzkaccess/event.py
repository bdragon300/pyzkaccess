import itertools
import time
from collections import deque
from copy import deepcopy
from datetime import datetime
from typing import Optional, List, Iterable, Union

from .enum import VERIFY_MODES, EVENT_TYPES, ENTRY_EXIT_TYPES
from .sdk import ZKSDK


class Event:
    """
    Represents one realtime event occured on the device
    Since the device returns event as string we need to parse it to the
    structured view. This class does this.
    """
    __slots__ = (
        'time',
        'pin',
        'card',
        'door',
        'event_type',
        'entry_exit',
        'verify_mode'
    )

    def __init__(self, s=None):
        """
        :param s: Optional. Event string to be parsed.
        """
        if s:
            self.parse(s)

    @property
    def description(self) -> str:
        msg = 'Event[{}]: "{}" at door "{}" for card "{}" -- {}'.format(
            str(self.time), self.event_type_description, self.door, self.card,
            self.entry_exit_description
        )
        return msg

    @property
    def entry_exit_description(self) -> str:
        return ENTRY_EXIT_TYPES.get(self.entry_exit, '?')

    @property
    def event_type_description(self) -> str:
        return EVENT_TYPES.get(self.event_type, '?')

    @property
    def verify_mode_description(self) -> str:
        return VERIFY_MODES.get(self.verify_mode, '?')

    def parse(self, event_line: str) -> None:
        """
        Parse one event string and fills out slots
        :param event_line: event string
        :raises ValueError: event string is invalid
        :return:
        """
        if event_line == '' or event_line == '\r\n':
            raise ValueError("Empty event string")

        items = event_line.split(',')
        if len(items) != 7:
            raise ValueError("Event string has not 7 comma-separated parts")

        for i in range(len(self.__slots__)):
            setattr(self, self.__slots__[i], items[i])

        self.time = datetime.strptime(self.time, '%Y-%m-%d %H:%M:%S')
        self.door = int(self.door)
        self.event_type = int(self.event_type)
        self.entry_exit = int(self.entry_exit)
        self.verify_mode = int(self.verify_mode)

    def __str__(self):
        return 'Event(' \
               + ', '.join('{}={}'.format(k, getattr(self, k)) for k in self.__slots__) \
               + ')'

    def __repr__(self):
        return self.__str__()


class EventLog:
    def __init__(self,
                 sdk: ZKSDK,
                 buffer_size: int,
                 maxlen: Optional[int] = None,
                 only_filters: Optional[dict] = None,
                 _data: Optional[deque] = None):
        self.sdk = sdk
        self.buffer_size = buffer_size
        self.data = _data if _data is not None else deque(maxlen=maxlen)
        self.only_filters = only_filters or {}

    def refresh(self) -> int:
        # ZKAccess always returns single event with code 255
        # on every log query if no other events occured. So, skip it
        new_events = [e for e in self._pull_events() if e.event_type != 255]
        count = 0
        while new_events:
            self.data.extend(new_events)
            count += sum(1 for _ in self._filtered_events(new_events))
            new_events = [e for e in self._pull_events() if e.event_type != 255]

        return min(len(self.data), count)

    def after_time(self, after_time: datetime) -> Iterable[Event]:
        return filter(lambda x: x.time >= after_time, self._filtered_events(self.data))

    def before_time(self, before_time: datetime) -> Iterable[Event]:
        return filter(lambda x: x.time < before_time, self._filtered_events(self.data))

    def between_time(self, from_time: datetime, to_time: datetime) -> Iterable[Event]:
        return filter(lambda x: from_time <= x.time < to_time, self._filtered_events(self.data))

    def poll(self, timeout: int = 60, polling_interval: int = 1) -> List[Event]:
        for _ in range(timeout):
            count = self.refresh()
            if count:
                reversed_events = self._filtered_events(reversed(self.data))
                res = list(itertools.islice(reversed_events, None, count))[::-1]
                return res
            time.sleep(polling_interval)

        return []

    def only(self, **filters) -> 'EventLog':
        only_filters = self._merge_filters(self.only_filters, filters)
        obj = self.__class__(self.sdk,
                             self.buffer_size,
                             self.data.maxlen,
                             only_filters,
                             _data=self.data)
        return obj

    def clear(self) -> None:
        self.data.clear()

    @staticmethod
    def _merge_filters(initial: dict, fltr: dict) -> dict:
        seq_types = (tuple, list)
        res = deepcopy(initial)
        for key, value in fltr.items():
            if not isinstance(value, seq_types):
                value = [value]

            if key in res:
                res[key].extend(value)
            else:
                res[key] = value

        return res

    def _filtered_events(self, data: Iterable[Event]) -> Iterable[Event]:
        if not self.only_filters:
            yield from data
            return

        for event in data:
            # ZKAccess always returns single event with code 255
            # on every log query if no other events occured. So, skip it
            if event.event_type == 255:
                continue

            if not self.only_filters:
                yield event
            else:
                all_match = all(getattr(event, field) in fltr
                                for field, fltr in self.only_filters.items())
                if all_match:
                    yield event

    def _pull_events(self) -> Iterable[Event]:
        events = self.sdk.get_rt_log(self.buffer_size)
        return (Event(s) for s in events)

    def __getitem__(self, item) -> Union[Iterable[Event], Event]:
        seq = self._filtered_events(self.data)
        if not isinstance(item, slice):
            try:
                return next(itertools.islice(seq, item, None))
            except StopIteration:
                raise IndexError('Index is out of range') from None

        start, stop, step = item.start, item.stop, item.step
        return itertools.islice(seq, start, stop, step)

    def __len__(self) -> int:
        if not self.only_filters:
            return len(self.data)

        return sum(1 for _ in self._filtered_events(self.data))

    def __iter__(self):
        return iter(self._filtered_events(self.data))

    def __str__(self):
        items_str = ', '.join(str(x) for x in self[:3])
        if len(self) > 6:
            items_str += ', ..., ' + ', '.join(str(x) for x in self[3:])
        return 'EventLog[{}]({})'.format(len(self), items_str)

    def __repr__(self):
        return self.__str__()
