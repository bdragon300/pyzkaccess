from itertools import zip_longest
from unittest.mock import Mock

import pytest

from pyzkaccess.event import EventLog
from pyzkaccess.reader import Reader, ReaderList


class TestReader:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.event_log = EventLog(self.sdk, 4096)

    def test_init__should_init_properties(self):
        obj = Reader(self.sdk, self.event_log, 2)

        assert obj._sdk is self.sdk
        assert obj._event_log is self.event_log
        assert obj.number == 2

    def test_events__should_return_new_eventlog_instance_with_filters(self):
        obj = Reader(self.sdk, self.event_log, 2)

        res = obj.events

        assert type(res) == EventLog
        assert res is not self.event_log
        assert res.only_filters == {
            'door': {2},
            'event_type': {0, 1, 2, 3, 4, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 26,
                           27, 29, 30, 31, 32, 33, 34, 35, 36, 101, 103, 203}
        }

    @pytest.mark.parametrize('val', (None, (), [], object, type))
    def test_eq__if_other_object_type__should_return_false(self, val):
        obj = Reader(self.sdk, self.event_log, 2)

        assert obj.__eq__(val) is False

    @pytest.mark.parametrize('number', (1, 2))
    def test_eq__should_return_comparing_result(self, number):
        obj = Reader(self.sdk, self.event_log, 2)
        other_obj = Reader(self.sdk, self.event_log, number)
        expect = obj.number == other_obj.number

        assert obj.__eq__(other_obj) == expect

    @pytest.mark.parametrize('val', (None, (), [], object, type))
    def test_ne__if_other_object_type__should_return_true(self, val):
        obj = Reader(self.sdk, self.event_log, 2)

        assert obj.__ne__(val) is True

    @pytest.mark.parametrize('number', (1, 2))
    def test_ne__should_return_comparing_result(self, number):
        obj = Reader(self.sdk, self.event_log, 2)
        other_obj = Reader(self.sdk, self.event_log, number)
        expect = not(obj.number == other_obj.number)

        assert obj.__ne__(other_obj) == expect

    def test_str__should_return_name_of_class(self):
        obj = Reader(self.sdk, self.event_log, 2)

        assert str(obj).startswith('Reader[')

    def test_repr__should_return_name_of_class(self):
        obj = Reader(self.sdk, self.event_log, 2)

        assert repr(obj).startswith('Reader[')


class TestReaderList:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.event_log = EventLog(self.sdk, 4096)
        self.readers = (
            Reader(self.sdk, self.event_log, 1),
            Reader(self.sdk, self.event_log, 2),
            Reader(self.sdk, self.event_log, 3),
        )
        self.obj = ReaderList(self.sdk, self.event_log, self.readers)

    def test_init__should_init_properties(self):
        assert self.obj._sdk is self.sdk
        assert self.obj._event_log is self.event_log
        assert all(a is b for a, b in zip_longest(self.obj, self.readers))

    def test_events__should_return_new_eventlog_instance_with_filters(self):
        res = self.obj.events

        assert type(res) == EventLog
        assert res.only_filters == {
            'door': {1, 2, 3},
            'event_type': {0, 1, 2, 3, 4, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 26,
                           27, 29, 30, 31, 32, 33, 34, 35, 36, 101, 103, 203}
        }

    def test_getitem__if_index_passed__should_return_item(self):
        assert type(self.obj[2]) == Reader
        assert self.obj[2].number == 3

    @pytest.mark.parametrize('idx', (
            slice(None, 1), slice(1, 2), slice(None, None, 2), slice(0, 0)
    ))
    def test_getitem__if_slice_passed__should_return_items(self, idx):
        res = self.obj[idx]

        assert type(res) == ReaderList
        assert all(a == b for a, b in zip_longest(res, self.readers[idx]))
