from itertools import zip_longest
from unittest.mock import Mock, call

import pytest

from pyzkaccess.enums import RelayGroup, ControlOperation
from pyzkaccess.relay import Relay, RelayList


class TestRelay:
    @pytest.mark.parametrize('group,number', ((RelayGroup.lock, 1), (RelayGroup.aux, 3)))
    def test_init__should_init_properties(self, group, number):
        sdk = Mock()

        obj = Relay(sdk, group, number)

        assert obj._sdk is sdk
        assert obj.group == group
        assert obj.number == number

    @pytest.mark.parametrize('group,number', ((RelayGroup.lock, 1), (RelayGroup.aux, 3)))
    def test_switch_on__should_call_sdk_method(self, group, number):
        sdk = Mock()
        obj = Relay(sdk, group, number)
        timeout = 45

        obj.switch_on(timeout)

        sdk.control_device.assert_called_once_with(
            ControlOperation.output.value, number, group.value, timeout, 0
        )

    @pytest.mark.parametrize('timeout', (-1, 256))
    def test_switch_on__if_timeout_is_out_of_range__should_raise_error(self, timeout):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)

        with pytest.raises(ValueError):
            obj.switch_on(timeout)

    @pytest.mark.parametrize('val', (None, (), [], object, type))
    def test_eq__if_other_object_type__should_return_false(self, val):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)

        assert obj.__eq__(val) is False

    @pytest.mark.parametrize('number', (1, 2))
    @pytest.mark.parametrize('group', (RelayGroup.lock, RelayGroup.aux))
    def test_eq__should_return_comparing_result(self, number, group):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)
        other_obj = Relay(sdk, group, number)
        expect = obj.number == other_obj.number and obj.group == other_obj.group

        assert obj.__eq__(other_obj) == expect

    @pytest.mark.parametrize('val', (None, (), [], object, type))
    def test_ne__if_other_object_type__should_return_true(self, val):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)

        assert obj.__ne__(val) is True

    @pytest.mark.parametrize('number', (1, 2))
    @pytest.mark.parametrize('group', (RelayGroup.lock, RelayGroup.aux))
    def test_ne__should_return_comparing_result(self, number, group):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)
        other_obj = Relay(sdk, group, number)
        expect = not(obj.number == other_obj.number and obj.group == other_obj.group)

        assert obj.__ne__(other_obj) == expect

    def test_str__should_return_name_of_class(self):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)

        assert str(obj).startswith('Relay.')

    def test_repr__should_return_name_of_class(self):
        sdk = Mock()
        obj = Relay(sdk, RelayGroup.lock, 2)

        assert repr(obj).startswith('Relay(')


class TestRelayList:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.relays = (
            Relay(self.sdk, RelayGroup.aux, 1),
            Relay(self.sdk, RelayGroup.aux, 2),
            Relay(self.sdk, RelayGroup.lock, 1),
            Relay(self.sdk, RelayGroup.lock, 2),
        )
        self.obj = RelayList(self.sdk, self.relays)

    def test_init__should_init_properties(self):
        assert self.obj._sdk is self.sdk
        assert all(a is b for a, b in zip_longest(self.obj, self.relays))

    def test_switch_on__should_call_sdk_method(self):
        timeout = 45

        self.obj.switch_on(timeout)

        self.sdk.control_device.assert_has_calls((
            call(ControlOperation.output.value, 1, RelayGroup.aux.value, timeout, 0),
            call(ControlOperation.output.value, 2, RelayGroup.aux.value, timeout, 0),
            call(ControlOperation.output.value, 1, RelayGroup.lock.value, timeout, 0),
            call(ControlOperation.output.value, 2, RelayGroup.lock.value, timeout, 0),
        ))

    @pytest.mark.parametrize('timeout', (-1, 256))
    def test_switch_on__if_timeout_is_out_of_range__should_raise_error(self, timeout):
        with pytest.raises(ValueError):
            self.obj.switch_on(timeout)

    def test_getitem__if_index_passed__should_return_item(self):
        assert type(self.obj[2]) == Relay
        assert self.obj[2].number == 1
        assert self.obj[2].group == RelayGroup.lock

    @pytest.mark.parametrize('idx', (
            slice(None, 2), slice(1, 3), slice(None, None, 2), slice(0, 0)
    ))
    def test_getitem__if_slice_passed__should_return_items(self, idx):
        res = self.obj[idx]

        assert type(res) == RelayList
        assert all(a == b for a, b in zip_longest(res, self.relays[idx]))

    @pytest.mark.parametrize('mask', (
        [1, 0, 1, 0],
        [0, 0, 0, 0],
        [0, 1],  # Should consider only two first relays
        [1, 0, 0, 1, 0, 1, 0]  # Should consider only 4 first values
    ))
    def test_by_mask__should_return_relays_according_given_mask(self, mask):
        expect = [r for m, r in zip(mask, self.obj) if m == 1]

        res = self.obj.by_mask(mask)

        assert type(res) == RelayList
        assert list(res) == expect
