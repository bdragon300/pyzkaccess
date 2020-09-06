import time
from collections import deque
from datetime import datetime
from unittest.mock import patch, Mock

import pytest

with patch('ctypes.WinDLL', create=True):
    from pyzkaccess.event import Event, EventLog
    from pyzkaccess.common import DocValue
    from pyzkaccess.enum import PassageDirection, VerifyMode


class TestEvent:
    @pytest.mark.parametrize('event_string', (
        '2000-02-02 15:09:10,0,7125793,1,27,2,0\r\n',
        '2000-02-02 15:09:10,0,7125793,1,27,2,0'
    ))
    def test_init__should_parse_and_fill_object_attributes(self, event_string):
        obj = Event(event_string)

        assert obj.time == datetime(2000, 2, 2, 15, 9, 10)
        assert obj.pin == '0'
        assert obj.card == '7125793'
        assert obj.door == 1
        assert obj.event_type == 27 and type(obj.event_type) == DocValue
        assert obj.entry_exit == PassageDirection(2)
        assert obj.verify_mode == VerifyMode(0)

    @pytest.mark.parametrize('device_string', (
        # String is duplicated
        '2000-02-02 15:09:10,0,7125793,1,27,2,0\r\n'
        '2000-02-02 15:09:10,0,7125793,1,27,2,0',

        # Fields count less than 7
        '2000-02-02 15:09:10,0,7125793,1,27,2',

        # Fields count more than 7
        '2000-02-02 15:09:10,0,7125793,1,27,2,0,asdf,33',

        # Wrong string
        'wrong_string',

        # Empty strings
        '\r\n',
        ''
    ))
    def test_init__if_device_string_is_incorrect__should_raise_error(self, device_string):
        with pytest.raises(ValueError):
            Event(device_string)

    def test_description__should_return_name_of_class(self):
        obj = Event('2000-02-02 15:09:10,0,7125793,1,27,2,0')

        assert obj.description.startswith('Event[')

    def test_str__should_return_name_of_class(self):
        obj = Event('2000-02-02 15:09:10,0,7125793,1,27,2,0')

        assert str(obj).startswith('Event(')

    def test_repr__should_return_name_of_class(self):
        obj = Event('2000-02-02 15:09:10,0,7125793,1,27,2,0')

        assert repr(obj).startswith('Event(')


class TestEventLog:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()

    def test_init__should_initialize_attributes(self):
        data = deque()
        filters = {'filter': {'value'}}
        obj = EventLog(self.sdk, 4096, 10, filters)

        assert obj._sdk is self.sdk
        assert obj.buffer_size == 4096
        assert obj.data.maxlen == 10
        assert obj.only_filters == filters
        assert type(obj.data) == deque

    def test_init__should_initialize_data_attribute(self):
        data = deque()
        filters = {'filter': {'value'}}
        obj = EventLog(self.sdk, 4096, 10, filters, data)

        assert obj._sdk is self.sdk
        assert obj.buffer_size == 4096
        assert obj.data.maxlen == None  # When _data is passed
        assert obj.only_filters == filters
        assert obj.data is data

    def test_init__if_data_is_omitted__should_create_empty_deque_with_given_maxlen(self):
        obj = EventLog(self.sdk, 4096, 10)

        assert type(obj.data) == deque
        assert obj.data.maxlen == 10
        assert len(obj.data) == 0

    def test_init__if_filters_are_omitted__should_create_empty_filters_dict(self):
        obj = EventLog(self.sdk, 4096)

        assert obj.only_filters == {}

    @pytest.mark.parametrize('initial,events_str,expect', (
        (
            [Event('2000-02-02 15:09:00,0,7125794,2,26,1,0')],
            ['2000-02-02 15:09:10,0,7125793,1,27,2,0',
             '2000-02-02 15:09:15,0,7125794,3,27,2,0',
             '2000-02-02 15:09:17,0,7125784,3,27,2,0'],
            (Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
             Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
             Event('2000-02-02 15:09:17,0,7125784,3,27,2,0'))
        ),
        (
            [Event('2000-02-02 15:09:00,0,7125794,2,26,1,0')],
            ['2000-02-02 15:09:10,0,7125793,1,27,2,0', '2000-02-02 15:09:15,0,7125794,3,27,2,0'],
            (Event('2000-02-02 15:09:00,0,7125794,2,26,1,0'),
             Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
             Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'))
        ),
        (
            [Event('2000-02-02 15:09:00,0,7125794,2,26,1,0')],
            ['2000-02-02 15:09:10,0,7125793,1,27,2,0'],
            (Event('2000-02-02 15:09:00,0,7125794,2,26,1,0'),
             Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'), )
        ),
    ))
    def test_refresh__if_device_has_returned_events_and_maxlen_is_set__should_append_data_and_return_count_of_fetched_records(  # noqa
            self, initial, events_str, expect
    ):
        self.sdk.get_rt_log.side_effect = [events_str, []]
        obj = EventLog(self.sdk, 4096, _data=deque(initial, maxlen=3))

        res = obj.refresh()

        assert tuple(obj.data) == expect
        assert res == len(events_str)

    @pytest.mark.parametrize('initial,events_str,expect,expect_len', (
        (
            [Event('2000-02-02 15:09:00,0,7125794,2,26,1,0')],
            ['2000-02-02 15:09:10,0,7125793,1,27,2,0',
             '2000-02-02 15:09:15,0,7125794,3,255,2,0',
             '2000-02-02 15:09:17,0,7125784,3,27,2,0'],
            (Event('2000-02-02 15:09:00,0,7125794,2,26,1,0'),
             Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
             Event('2000-02-02 15:09:17,0,7125784,3,27,2,0')),
            2
        ),
        (
            [Event('2000-02-02 15:09:00,0,7125794,2,26,1,0')],
            ['2000-02-02 15:09:15,0,7125794,3,255,2,0'],
            (Event('2000-02-02 15:09:00,0,7125794,2,26,1,0'), ),
            0
        ),
    ))
    def test_refresh__if_device_has_returned_events__should_always_skip_event_type_255(
            self, initial, events_str, expect, expect_len
    ):
        self.sdk.get_rt_log.side_effect = [events_str, []]
        obj = EventLog(self.sdk, 4096, _data=deque(initial))

        res = obj.refresh()

        assert tuple(obj.data) == expect
        assert res == expect_len

    def test_refresh__if_device_has_returned_events__and_filters_and_maxlen_are_set__should_append_filtered_data_and_return_count_of_matched_records(self):  # noqa
        events_strings = [
            '2000-02-02 15:09:10,0,7125793,1,27,2,0',
            '2000-02-02 15:09:15,0,7125794,3,27,2,0',
            '2000-02-02 15:09:17,0,7125784,1,25,2,0',
            '2000-02-02 15:09:20,0,7125793,3,27,2,0',
            '2000-02-02 15:09:21,0,7125794,2,26,1,0'
        ]
        events_inserted = (
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        )
        self.sdk.get_rt_log.side_effect = [events_strings, []]
        obj = EventLog(self.sdk, 4096, 2, only_filters={'card': {'7125794', '7125784'}})

        res = obj.refresh()

        assert tuple(obj.data) == events_inserted  # 2 records inserted due to maxlen
        assert res == 3  # 3 records matched

    def test_after_time__should_return_records_after_datetime_included(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)
        dt = datetime(2000, 2, 2, 15, 9, 17)

        res = obj.after_time(dt)

        assert tuple(res) == (
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        )

    def test_before_time__should_return_records_before_datetime_excluded(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)
        dt = datetime(2000, 2, 2, 15, 9, 17)

        res = obj.before_time(dt)

        assert tuple(res) == (
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0')
        )

    def test_between_time__should_return_records_betwenn_datetimes(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)
        dt1 = datetime(2000, 2, 2, 15, 9, 15)
        dt2 = datetime(2000, 2, 2, 15, 9, 20)

        res = obj.between_time(dt1, dt2)

        assert tuple(res) == (
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
        )

    def test_poll__if_refresh_returned_events__should_return_new_events(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        with patch.object(obj, 'refresh', Mock(side_effect=(0, 0, 2))):
            res = obj.poll(60, polling_interval=.5)

            assert res == list(data)[-2:]

    def test_poll__if_refresh_returned_events_and_filters_specified__should_return_new_filtered_events(  # noqa
            self
    ):
        data = [
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ]
        expect = (
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        )
        obj = EventLog(self.sdk, 4096, only_filters={'card': {'7125794', '7125784'}})

        with patch.object(obj, '_pull_events', Mock(side_effect=([], [], data, []))):
            res = obj.poll(60, polling_interval=.5)

            assert tuple(res) == expect

    def test_poll__if_refresh_returned_events_on_3rd_time__should_hang_for_2_intervals(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        with patch.object(obj, 'refresh', Mock(side_effect=(0, 0, 2))):
            start = datetime.now()
            obj.poll(60, polling_interval=.5)
            seconds = (datetime.now() - start).seconds

            assert 1 <= seconds < 1.5

    def test_poll__if_refresh_does_not_returned_result__should_return_empty_result_on_timeout(self):
        def refresh_with_slow_network():
            time.sleep(.2)
            return 0

        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        with patch.object(obj, 'refresh', Mock(wraps=refresh_with_slow_network)):
            start = datetime.now()
            res = obj.poll(2, polling_interval=.5)
            seconds = (datetime.now() - start).seconds

            assert 2 <= seconds < 2.5
            assert res == []

    def test_only__should_return_new_instance(self):
        obj = EventLog(self.sdk, 4096, 2)

        res = obj.only(card=(2, ))

        assert type(res) == EventLog
        assert res is not obj
        assert res._sdk is obj._sdk
        assert res.buffer_size == obj.buffer_size
        assert res.data.maxlen == obj.data.maxlen
        assert res.only_filters == {'card': {2}}
        assert res.data is obj.data

    @pytest.mark.parametrize('initial_filters,filters,expect', (
        ({}, {'event_type': {33, 44}, 'door': 1}, {'event_type': {33, 44}, 'door': {1}}),
        (
            {'event_type': {44, 55}},
            {'event_type': {33, 44}, 'door': [1]},
            {'event_type': {33, 44, 55}, 'door': {1}}
        ),
        (
            {'event_type': {44, 55}},
            {'event_type': (33, 44), 'door': 1},
            {'event_type': {33, 44, 55}, 'door': {1}}
        )
    ))
    def test_only__should_return_instance_with_merged_filters(
            self, initial_filters, filters, expect
    ):
        obj = EventLog(self.sdk, 4096, 2, only_filters=initial_filters)

        res = obj.only(**filters)

        assert res.only_filters == expect

    def test_clear__should_clear_data(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        obj.clear()

        assert len(obj.data) == 0

    def test_getitem__if_index_passed__should_return_item(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        assert type(obj[2]) == Event
        assert obj[2] == data[2]

    def test_getitem__if_index_passed_and_out_or_range__should_raise_error(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        with pytest.raises(IndexError):
            _ = obj[10]

    @pytest.mark.parametrize('idx', (
            slice(None, 2), slice(1, 3), slice(None, None, 2), slice(0, 0)
    ))
    def test_getitem__if_slice_passed__should_return_items(self, idx):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        assert list(obj[idx]) == list(data)[idx]

    def test_getitem__if_index_passed_and_filters_specified__should_return_filtered_items(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, only_filters={'card': {'7125794', '7125793'}}, _data=data)

        assert type(obj[2]) == Event
        assert obj[2] == data[3]

    def test_getitem__if_index_passed_and_filters_specified_and_out_of_range__should_raise_error(
            self
    ):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, only_filters={'card': {'7125794', '7125793'}}, _data=data)

        with pytest.raises(IndexError):
            _ = obj[4]

    @pytest.mark.parametrize('idx', (
            slice(None, 2), slice(1, 3), slice(None, None, 2), slice(0, 0)
    ))
    def test_getitem__if_slice_passed_and_filters_specified__should_return_filtered_items(
            self, idx
    ):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        consider_data = [
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ]
        obj = EventLog(self.sdk, 4096, only_filters={'card': {'7125794', '7125793'}}, _data=data)

        assert list(obj[idx]) == consider_data[idx]

    def test_len__should_return_data_length(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        assert len(obj) == len(data)

    def test_len__if_filters_specified__should_return_filtered_data_length(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        consider_data = [
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ]
        obj = EventLog(self.sdk, 4096, only_filters={'card': {'7125794', '7125793'}}, _data=data)

        assert len(obj) == len(consider_data)

    def test_iter__should_iter_over_data(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        obj = EventLog(self.sdk, 4096, _data=data)

        assert len(obj) == len(data)

    def test_iter__if_filters_specified__should_iter_over_filtered_data(self):
        data = deque((
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:17,0,7125784,1,25,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ))
        consider_data = [
            Event('2000-02-02 15:09:10,0,7125793,1,27,2,0'),
            Event('2000-02-02 15:09:15,0,7125794,3,27,2,0'),
            Event('2000-02-02 15:09:20,0,7125793,3,27,2,0'),
            Event('2000-02-02 15:09:21,0,7125794,2,26,1,0')
        ]
        obj = EventLog(self.sdk, 4096, only_filters={'card': {'7125794', '7125793'}}, _data=data)

        assert list(obj) == consider_data

    def test_str__should_return_name_of_class(self):
        obj = EventLog(self.sdk, 4096)

        assert str(obj).startswith('EventLog[')

    def test_repr__should_return_name_of_class(self):
        obj = EventLog(self.sdk, 4096)

        assert repr(obj).startswith('EventLog[')
