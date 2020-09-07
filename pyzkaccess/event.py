__all__ = [
    'Event',
    'EventLog'
]
import itertools
import time
from collections import deque
from copy import deepcopy
from datetime import datetime
from typing import Optional, List, Iterable, Union, Sequence

from .common import DocValue
from .enum import VerifyMode, PassageDirection, EVENT_TYPES
from .sdk import ZKSDK


class Event:
    """
    One realtime event occured on the device
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

    def __init__(self, s):
        """
        :param s: Event string to be parsed.
        """
        parsed = self.parse(s)

        self.time = datetime.strptime(parsed[0], '%Y-%m-%d %H:%M:%S')  # type: datetime
        self.pin = parsed[1]   # type: str
        self.card = parsed[2]  # type: str
        self.door = int(parsed[3])  # type: int
        self.event_type = EVENT_TYPES[int(parsed[4])]  # type: DocValue
        self.entry_exit = PassageDirection(int(parsed[5]))  # type: PassageDirection
        self.verify_mode = VerifyMode(int(parsed[6]))  # type: VerifyMode

    @property
    def description(self) -> str:
        msg = 'Event[{}]: "{}" at door "{}" for card "{}" -- {}'.format(
            str(self.time), self.event_type.doc, self.door, self.card,
            self.entry_exit.name.capitalize()
        )
        return msg

    @staticmethod
    def parse(event_line: str) -> Sequence[str]:
        """
        Parse raw event string
        :param event_line: event string
        :return: parsed string parts of event string
        """
        event_line = event_line.replace('\r\n', '')

        items = event_line.split(',')
        if len(items) != 7:
            raise ValueError("Event string must have exactly 7 parts: {}".format(event_line))

        return items

    def __eq__(self, other):
        if isinstance(other, Event):
            return all(getattr(self, attr) == getattr(other, attr) for attr in self.__slots__)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'Event(' \
               + ', '.join('{}={}'.format(k, getattr(self, k)) for k in self.__slots__) \
               + ')'

    def __repr__(self):
        return self.__str__()


class EventLog:
    """Log of realtime events

    Keep in mind that log is not filled out automatically and
    should be refreshed periodically by hand using `refresh()`
    method. This is because working with ZKAccess has
    request-response nature and cannot up a tunnel which may be
    used to feed events.

    But you can use `poll()` method which awaits new events from
    a device and return them if any.

    Log is implemented at top of deque structure, so accessing by
    index and filtering could be slow.
    """
    def __init__(self,
                 sdk: ZKSDK,
                 buffer_size: int,
                 maxlen: Optional[int] = None,
                 only_filters: Optional[dict] = None,
                 _data: Optional[deque] = None):
        self.buffer_size = buffer_size
        self.data = _data if _data is not None else deque(maxlen=maxlen)
        self.only_filters = only_filters or {}
        self._sdk = sdk

    def refresh(self) -> int:
        """Make a request to a device for new records and append to the
        end if any.
        :return: count of records which was added
        """
        # ZKAccess always returns single event with code 255
        # on every log query if no other events occured. So, skip it
        new_events = [e for e in self._pull_events() if e.event_type != 255]
        count = 0
        while new_events:
            self.data.extend(new_events)
            count += sum(1 for _ in self._filtered_events(new_events))
            new_events = [e for e in self._pull_events() if e.event_type != 255]

        return count

    def after_time(self, after_time: datetime) -> Iterable[Event]:
        """
        Return events which was occured after given time
        :param after_time: datetime object to filter (included)
        :return:
        """
        return filter(lambda x: x.time >= after_time, self._filtered_events(self.data))

    def before_time(self, before_time: datetime) -> Iterable[Event]:
        """
        Return events which was occured before given time
        :param before_time: datetime object to filter (excluded)
        :return:
        """
        return filter(lambda x: x.time < before_time, self._filtered_events(self.data))

    def between_time(self, from_time: datetime, to_time: datetime) -> Iterable[Event]:
        """
        Return events which was occured between two given time moments
        :param from_time: datetime object to filter (included)
        :param to_time: datetime object to filter (excluded)
        :return:
        """
        return filter(lambda x: from_time <= x.time < to_time, self._filtered_events(self.data))

    def poll(self, timeout: float = 60, polling_interval: float = 1) -> List[Event]:
        """
        Wait for new events by making periodically requests to a device.
        If events was appeared then return them. If no event was
        appeared until timeout was expired then return empty iterable.
        :param timeout: timeout in seconds. Default: 60 seconds
        :param polling_interval: interval to make a requests in seconds.
         Default: every 1 second
        :return: iterable with new events if any or empty iterable if
         timeout has expired
        """
        deadline = datetime.now().timestamp() + timeout
        while datetime.now().timestamp() < deadline:
            count = self.refresh()  # Can run up to several seconds depending on network
            if count:
                reversed_events = self._filtered_events(reversed(self.data))
                res = list(itertools.islice(reversed_events, None, count))[::-1]
                return res
            time.sleep(polling_interval)

        return []

    def only(self, **filters) -> 'EventLog':
        """
        Return new EventLog instance with given filters applied.
        Kwargs names must be the same as Event slots.

        Event log returned by this method will contain entries in
        which attribute value is contained in appropriate filter
        (if any).

        Filters passed here will be ANDed during comparison. On
        repeatable call of only, given filters which was also set
        on previous call will be ORed, i.e. their values will be
        concatenated.

        In other words:

        ```log.only(a=2, b=['x', 'y'])` => filtering(entry.a == 2 AND entry.b in ('x', 'y'))```

        ```log.only(a=2, b=['x', 'y']).only(a=3, b=5, c=1) =>
            filtering(entry.a in (2, 3) AND entry.b in ('x', 'y', 5) and entry.c == 1)```

        Ex: `new_log = log.only(door=1, event_type=221)`
        :param filters:
        :return: new fitlered EventLog instance
        """
        only_filters = self._merge_filters(self.only_filters, filters)
        obj = self.__class__(self._sdk,
                             self.buffer_size,
                             self.data.maxlen,
                             only_filters,
                             _data=self.data)
        return obj

    def clear(self) -> None:
        """Clear log"""
        self.data.clear()

    @staticmethod
    def _merge_filters(initial: dict, fltr: dict) -> dict:
        """
        Merge two filter dicts, fltr updates initial. Key-values  which
        does not exist in initial will be copied. Value of existent
        keys are combined (values always are lists).
        :param initial: updating initial filter dict
        :param fltr: filter dict which updates initial
        :return: merged filter dict
        """
        seq_types = (tuple, list, set, frozenset)
        res = deepcopy(initial)
        for key, value in fltr.items():
            if not isinstance(value, seq_types):
                value = {value}

            if key in res:
                res[key].update(value)
            else:
                res[key] = set(value)

        return res

    def _filtered_events(self, data: Iterable[Event]) -> Iterable[Event]:
        """
        Apply current filters to given events and return only events
        which meet them
        :param data: unfiltered events
        :return: filtered events
        """
        if not self.only_filters:
            yield from data
            return

        for event in data:
            if not self.only_filters:
                yield event
            else:
                all_match = all(getattr(event, field) in fltr
                                for field, fltr in self.only_filters.items())
                if all_match:
                    yield event

    def _pull_events(self) -> Iterable[Event]:
        events = self._sdk.get_rt_log(self.buffer_size)
        return (Event(s) for s in events)

    def __getitem__(self, item: Union[int, slice]) -> Union[Iterable[Event], Event]:
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
