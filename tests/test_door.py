from itertools import zip_longest
from unittest.mock import Mock

import pytest

from pyzkaccess.aux_input import AuxInput, AuxInputList
from pyzkaccess.device import ZK200
from pyzkaccess.door import Door, DoorList
from pyzkaccess.enum import RelayGroup
from pyzkaccess.event import EventLog
from pyzkaccess.param import DoorParameters
from pyzkaccess.reader import Reader, ReaderList
from pyzkaccess.relay import Relay, RelayList


class TestDoor:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.event_log = EventLog(self.sdk, 4096)
        self.door_number = 2
        self.relays = (
            Relay(self.sdk, RelayGroup.lock, 1),
            Relay(self.sdk, RelayGroup.aux, 1),
        )
        self.relay_list = RelayList(self.sdk, self.relays)
        self.reader = Reader(self.sdk, self.event_log, self.door_number)
        self.aux_input = AuxInput(self.sdk, self.event_log, self.door_number)
        self.parameters = DoorParameters(self.sdk, ZK200, self.door_number)
        self.obj = Door(self.sdk, self.event_log, self.door_number,
                        self.relay_list, self.reader, self.aux_input, self.parameters)

    def test_init__should_init_properties(self):
        assert self.obj._sdk is self.sdk
        assert self.obj._event_log is self.event_log
        assert self.obj._relays is self.relay_list
        assert self.obj._reader is self.reader
        assert self.obj._aux_input is self.aux_input
        assert self.obj._parameters is self.parameters
        assert self.obj.number == self.door_number

    def test_events__should_return_new_eventlog_instance_with_filters(self):
        res = self.obj.events

        assert type(res) == EventLog
        assert res is not self.event_log
        assert res.only_filters == {'door': {self.door_number}}

    def test_relays__should_return_relays_object(self):
        res = self.obj.relays

        assert res is self.relay_list

    def test_reader__should_return_reader_object(self):
        res = self.obj.reader

        assert res is self.reader

    def test_aux_input__should_return_aux_input_object(self):
        res = self.obj.aux_input

        assert res is self.aux_input

    def test_parameters__should_return_parameters_object(self):
        res = self.obj.parameters

        assert res is self.parameters

    @pytest.mark.parametrize('val', (None, (), [], object, type))
    def test_eq__if_other_object_type__should_return_false(self, val):
        assert self.obj.__eq__(val) is False

    @pytest.mark.parametrize('number', (1, 2))
    def test_eq__should_return_comparing_result(self, number):
        other_obj = Door(self.sdk, self.event_log, number,
                         self.relay_list, self.reader, self.aux_input, self.parameters)
        expect = self.obj.number == other_obj.number

        assert self.obj.__eq__(other_obj) == expect

    @pytest.mark.parametrize('val', (None, (), [], object, type))
    def test_ne__if_other_object_type__should_return_true(self, val):
        assert self.obj.__ne__(val) is True

    @pytest.mark.parametrize('number', (1, 2))
    def test_ne__should_return_comparing_result(self, number):
        other_obj = Door(self.sdk, self.event_log, number,
                         self.relay_list, self.reader, self.aux_input, self.parameters)
        expect = not(self.obj.number == other_obj.number)

        assert self.obj.__ne__(other_obj) == expect

    def test_str__should_return_name_of_class(self):
        assert str(self.obj).startswith('Door[')

    def test_repr__should_return_name_of_class(self):
        assert repr(self.obj).startswith('Door[')


class TestDoorList:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.event_log = EventLog(self.sdk, 4096)
        self.doors = (
            Door(
                self.sdk,
                self.event_log,
                1,
                RelayList(self.sdk, (Relay(self.sdk, RelayGroup.lock, 1),
                                     Relay(self.sdk, RelayGroup.aux, 1))),
                Reader(self.sdk, self.event_log, 1),
                AuxInput(self.sdk, self.event_log, 1),
                DoorParameters(self.sdk, ZK200, 1)
            ),
            Door(
                self.sdk,
                self.event_log,
                2,
                RelayList(self.sdk, (Relay(self.sdk, RelayGroup.lock, 2),
                                     Relay(self.sdk, RelayGroup.aux, 2))),
                Reader(self.sdk, self.event_log, 2),
                AuxInput(self.sdk, self.event_log, 2),
                DoorParameters(self.sdk, ZK200, 2)
            )
        )
        self.obj = DoorList(self.sdk, self.event_log, self.doors)

    def test_init__should_init_properties(self):
        assert self.obj._sdk is self.sdk
        assert self.obj._event_log is self.event_log
        assert all(a is b for a, b in zip_longest(self.obj, self.doors))

    def test_events__should_return_new_eventlog_instance_with_filters(self):
        res = self.obj.events

        assert type(res) == EventLog
        assert res.only_filters == {'door': {1, 2}}

    def test_relays__should_return_relays_object(self):
        res = self.obj.relays

        assert type(res) == RelayList
        assert res == (
            Relay(self.sdk, RelayGroup.lock, 1),
            Relay(self.sdk, RelayGroup.aux, 1),
            Relay(self.sdk, RelayGroup.lock, 2),
            Relay(self.sdk, RelayGroup.aux, 2)
        )

    def test_readers__should_return_reader_objects(self):
        res = self.obj.readers

        assert type(res) == ReaderList
        assert res == (
            Reader(self.sdk, self.event_log, 1),
            Reader(self.sdk, self.event_log, 2)
        )

    def test_aux_inputs__should_return_aux_input_objects(self):
        res = self.obj.aux_inputs

        assert type(res) == AuxInputList
        assert res == (
            AuxInput(self.sdk, self.event_log, 1),
            AuxInput(self.sdk, self.event_log, 2)
        )

    def test_getitem__if_index_passed__should_return_item(self):
        assert type(self.obj[1]) == Door
        assert self.obj[1].number == 2

    @pytest.mark.parametrize('idx', (
            slice(None, 1), slice(1, 2), slice(None, None, 2), slice(0, 0)
    ))
    def test_getitem__if_slice_passed__should_return_items(self, idx):
        res = self.obj[idx]

        assert type(res) == DoorList
        assert all(a == b for a, b in zip_longest(res, self.doors[idx]))
