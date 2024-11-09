__all__ = ["Event", "EventLog"]
import itertools
import time
from collections import deque
from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable, Iterator, List, Optional, TypeVar, Union

from pyzkaccess.common import DocValue, ZKDatetimeUtils
from pyzkaccess.enums import EVENT_TYPES, PassageDirection, VerifyMode
from pyzkaccess.sdk import ZKSDK


class Event:
    """Represents a single event record from the device event log"""

    __slots__ = ("time", "pin", "card", "door", "event_type", "entry_exit", "verify_mode")

    def __init__(self, s: str):
        """Event constructor. Accepts a raw event string and parses
        it into predefined fields.

        Args:
            s (str): Raw event string

        """
        parsed = self.parse(s)

        self.time: datetime = ZKDatetimeUtils.time_string_to_datetime(parsed[0])
        self.pin: str = parsed[1]
        self.card: str = parsed[2]
        self.door: int = int(parsed[3])
        self.event_type: DocValue = EVENT_TYPES[int(parsed[4])]
        self.entry_exit: PassageDirection = PassageDirection(int(parsed[5]))
        self.verify_mode: VerifyMode = VerifyMode(int(parsed[6]))

    @property
    def description(self) -> str:
        msg = (
            f'Event[{self.time}]: "{self.event_type.doc}" at door "{self.door}" for card "{self.card}" -- '
            f"{self.entry_exit.name.capitalize()}]"
        )
        return msg

    @staticmethod
    def parse(event_line: str) -> List[str]:
        """Split a raw event string into parts

        Args:
            event_line (str): event string

        Returns:
            List[str]: parsed string parts of event string

        """
        event_line = event_line.replace("\r\n", "")

        items = event_line.split(",")
        if len(items) != 7:
            raise ValueError(f"Event string must have exactly 7 parts: {event_line}")

        return items

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Event):
            return all(getattr(self, attr) == getattr(other, attr) for attr in self.__slots__)
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f"Event({', '.join([f'{k}={getattr(self, k)}' for k in self.__slots__])})"

    def __repr__(self) -> str:
        return self.__str__()


EventLogT = TypeVar("EventLogT", bound="EventLog")


class EventLog:
    """Device event log.

    This class is a wrapper around a deque with fixed length.

    This log is *not* updated automatically, you should call
    `refresh()` method to gather new events from a device. This
    is because the PULL SDK has request-response nature.

    The most common way to keep the log up-to-date is to call
    `refresh()` in a loop in a separate thread. An example:

        >>> import threading
        >>> from pyzkaccess import ZKAccess
        >>> connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        >>> zk = ZKAccess(connstr=connstr)
        >>>
        >>> def refresh_loop():
        ...     while not stop_event.is_set():
        ...         with lock:
        ...             zk.events.refresh()
        >>>
        >>> stop_event = threading.Event()
        >>> lock = threading.RLock()
        >>> thread = threading.Thread(target=refresh_loop)
        >>> thread.start()
        >>>
        >>> # <do something with event log>
        >>>
        >>> # Stop the thread
        >>> stop_event.set()
        >>> thread.join()

    A more convenient way to get events in live mode is using the
    `poll()`. For example:

        >>> import threading
        >>> from pyzkaccess import ZKAccess
        >>> connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        >>> zk = ZKAccess(connstr=connstr)
        >>>
        >>> # Print new events in live mode (or exit after 60 seconds if nothing appeared since last poll)
        >>> while events := zk.events.poll():
        ...     for event in events:
        ...         print(event)
    """

    def __init__(
        self,
        sdk: ZKSDK,
        buffer_size: int,
        maxlen: Optional[int] = None,
        only_filters: Optional[dict] = None,
        _data: Optional[deque] = None,
    ):
        self.buffer_size = buffer_size
        self.data = _data if _data is not None else deque(maxlen=maxlen)
        self.only_filters = only_filters or {}
        self._sdk = sdk

    def refresh(self) -> int:
        """Make a request to a device for new records and append to the
        end if any.

        Returns:
            int: count of records which was added
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
        """Return events which was occured after given time

        Args:
            after_time (datetime): datetime object to filter (included)

        Returns:
            Iterable[Event]: events
        """
        return (x for x in self._filtered_events(self.data) if x.time >= after_time)

    def before_time(self, before_time: datetime) -> Iterable[Event]:
        """Return events which was occured before given time

        Args:
            before_time (datetime): datetime object to filter (excluded)

        Returns:
            Iterable[Event]: events
        """
        return (x for x in self._filtered_events(self.data) if x.time < before_time)

    def between_time(self, from_time: datetime, to_time: datetime) -> Iterable[Event]:
        """Return events which was occured between two given time moments

        Args:
            from_time (datetime): datetime object to filter (included)
            to_time (datetime): datetime object to filter (excluded)

        Returns:
            Iterable[Event]: events
        """
        return (x for x in self._filtered_events(self.data) if from_time <= x.time < to_time)

    def poll(self, timeout: float = 60, polling_interval: float = 1) -> List[Event]:
        """Wait for new events by making periodically requests to a device.
        Repeatedly checks for new events every `polling_interval` seconds.
        Once the new events are appeared, return them. If no event was
        appeared until the timeout was expired then return empty list.

        Args:
            timeout (float, default=60): timeout in seconds
            polling_interval (float, default=1): interval to make a requests
                in seconds

        Returns:
            List[Event]: events iterable with new events if any
                or empty iterable if timeout has expired

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

    def where_or(self: EventLogT, **filters: Any) -> EventLogT:
        """Apply filters to the event log. Filter names must follow the
        Event slots names.

        Filters in one call will be ANDed. The same filters in repeated
        calls will be ORed.

        A filter value of a sequence type (list, tuple, set, frozenset)
        are treated as a set of possible values, i.e. they will be ORed.

        In other words::

            # card == 2 AND door in (1, 2)
            log.where_or(card="123456", door=[1, 2])
            # card in ("123456", "654321") AND door in (1, 2, 3) AND pin == "1234"
            log.where_or(card="123456", door=[1, 2]).where_or(card="654321", door=3, pin="1234")

        Method returns a copy of EventLog with filters applied.

        Args:
            **filters (Any): filter values or list of them

        Returns:
            EventLog: a copy of EventLog with filters applied.

        """

        merged_filters = self._merge_filters(self.only_filters, filters)
        obj = self.__class__(self._sdk, self.buffer_size, self.data.maxlen, merged_filters, _data=self.data)
        return obj

    def only(self: EventLogT, **filters: Any) -> EventLogT:
        """Alias for `where_or` method, see its description for details"""
        return self.where_or(**filters)

    def clear(self) -> None:
        """Clear log"""
        self.data.clear()

    @staticmethod
    def _merge_filters(initial: dict, updates: dict) -> dict:
        """Merge two filter dict values.

        Args:
          initial (dict): updating initial filter dict
          updates (dict): filter dict which updates initial

        Returns:
          dict: merged filter dict

        """
        seq_types = (tuple, list, set, frozenset)
        res = deepcopy(initial)
        for key, value in updates.items():
            vals = {value} if not isinstance(value, seq_types) else value

            if key in res:
                res[key].update(vals)
            else:
                res[key] = set(vals)

        return res

    def _filtered_events(self, data: Iterable[Event]) -> Iterable[Event]:
        """Return the events from the data which match the current filters.

        Args:
          data (Iterable[Event]): unfiltered events

        Returns:
          Iterable[Event]: filtered events

        """
        if not self.only_filters:
            yield from data
            return

        for event in data:
            if not self.only_filters:
                yield event
            else:
                all_match = all(getattr(event, field) in fltr for field, fltr in self.only_filters.items())
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
                raise IndexError("Index is out of range") from None

        start, stop, step = item.start, item.stop, item.step
        return itertools.islice(seq, start, stop, step)

    def __len__(self) -> int:
        if not self.only_filters:
            return len(self.data)

        return sum(1 for _ in self._filtered_events(self.data))

    def __iter__(self) -> Iterator[Event]:
        return iter(self._filtered_events(self.data))

    def __str__(self) -> str:
        items_str = ", \n".join(str(x) for x in self)
        return f"{self.__class__.__name__}[{len(self)}](\n{items_str}\n)"

    def __repr__(self) -> str:
        return self.__str__()
