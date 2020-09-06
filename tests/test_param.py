from unittest.mock import patch, Mock, call
import pytest
from datetime import datetime
from enum import Enum


with patch('ctypes.WinDLL', create=True):
    from pyzkaccess.param import (
        DaylightSavingMomentMode1,
        DaylightSavingMomentMode2,
        DeviceParameters,
        DoorParameters
    )
    from pyzkaccess.enum import SensorType, VerifyMode
    from pyzkaccess.device import ZK100, ZK200, ZK400


# (property, parameter_name, property_type, correct_values, wrong_values)
daylight_saving_mode2_properties = (
    ('month', ('WeekOfMonth1', 'WeekOfMonth6'), int, [1, 12], [0, -1, 13]),
    ('week_of_month', ('WeekOfMonth2', 'WeekOfMonth7'), int, [1, 6], [0, -1, 7]),
    ('day_of_week', ('WeekOfMonth3', 'WeekOfMonth8'), int, [1, 7], [0, -1, 8]),
    ('hour', ('WeekOfMonth4', 'WeekOfMonth9'), int, [0, 23], [-1, 24]),
    ('minute', ('WeekOfMonth5', 'WeekOfMonth10'), int, [0, 59], [-1, 60]),
)


# (property, parameter_name, property_type, correct_values, wrong_values)
device_params_read_only = (
    ('serial_number', '~SerialNumber', str, ['asdf', ''], []),
    ('lock_count', 'LockCount', int, ['2'], ['asdf', '']),
    ('reader_count', 'ReaderCount', int, ['2'], ['asdf', '']),
    ('aux_in_count', 'AuxInCount', int, ['2'], ['asdf', '']),
    ('aux_out_count', 'AuxOutCount', int, ['2'], ['asdf', '']),
    # reboot
    ('fingerprint_version', '~ZKFPVersion', str, ['10'], []),
)


# (property, parameter_name, property_type, correct_values, wrong_values)
device_params_read_write = (
    ('communication_password', 'ComPwd', str, ['asdf', ''], []),
    ('ip_address', 'IPAddress', str, ['192.168.1.201'], ['', 'asdf', '1.2.3']),
    ('netmask', 'NetMask', str, ['192.168.1.255'], ['', 'asdf', '1.2.3']),
    ('gateway_ip_address', 'GATEIPAddress', str, ['192.168.1.201'], ['', 'asdf', '1.2.3']),
    ('rs232_baud_rate', 'RS232BaudRate', int, ['32165'], ['asdf', '']),
    ('watchdog_enabled', 'WatchDog', bool, ['1', '0'], ['asdf', '']),
    ('door4_to_door2', 'Door4ToDoor2', bool, ['1', '0'], ['asdf', '']),
    ('backup_hour', 'BackupTime', int, ['2'], ['asdf', '', '-1', '0', '25']),
    ('reader_direction', 'InBIOTowWay', str, ['1', '0'], []),
    ('display_daylight_saving', '~DSTF', bool, ['1', '0'], ['asdf', '']),
    ('enable_daylight_saving', 'DaylightSavingTimeOn', bool, ['1', '0'], ['asdf', '']),
    ('daylight_saving_mode', 'DLSTMode', int, ['1', '0'], ['asdf', '']),
    ('anti_passback_rule', 'AntiPassback', int, ['16', '0', '128'], ['asdf', '']),
    ('interlock', 'InterLock', int, ['0', '5'], ['asdf', '', '-1', '6']),
    (
        'spring_daylight_time_mode1', 'DaylightSavingTime', DaylightSavingMomentMode1,
        ['2-2-2-2'], ['', '0']
    ),
    (
        'fall_daylight_time_mode1', 'StandardTime', DaylightSavingMomentMode1,
        ['2-2-2-2'], ['', '0']
    ),
    ('datetime', 'DateTime', datetime, ['347748895'], ['asdf', '']),
    # spring_daylight_time_mode2
    # fall_daylight_time_mode2
)


# (property, parameter_name, property_type, correct_values, wrong_values)
door_params_read_write = (
    ('duress_password', 'ForcePassWord', str, ['', 'asdf'], []),
    ('emergency_password', 'SupperPassWord', str, ['', 'asdf'], []),
    ('lock_on_close', 'CloseAndLock', bool, ['1', '0'], ['asdf', '']),
    ('sensor_type', 'SensorType', SensorType, ['0', '2'], ['asdf', '', '-1', '3']),
    ('lock_driver_time', 'Drivertime', int, ['0', '255'], ['asdf', '', '-1', '256']),
    ('magnet_alarm_duration', 'Detectortime', int, ['0', '255'], ['asdf', '', '-1', '256']),
    (
        'verify_mode', 'VerifyType', VerifyMode,
        ['0', '1', '3', '4', '6', '10', '11', '200'], ['asdf', '', '-1', '2', '100', '201']
    ),
    ('multi_card_open', 'MultiCardOpenDoor', bool, ['1', '0'], ['asdf', '']),
    ('first_card_open', 'FirstCardOpenDoor', bool, ['1', '0'], ['asdf', '']),
    ('active_time_tz', 'ValidTZ', int, ['0', '128'], ['asdf', '']),
    ('open_time_tz', 'KeepOpenTimeZone', int, ['0', '128'], ['asdf', '']),
    ('punch_interval', 'Intertime', int, ['0', '128'], ['asdf', '']),
    ('cancel_open_day', 'CancelKeepOpenDay', int, ['0', '128'], ['asdf', ''])
)


def get_test_combinations(test_cases, correct):
    for prop, param, prop_type, correct_vals, wrong_vals in test_cases:
        sdk_vals = correct_vals if correct else wrong_vals
        for sdk_val in sdk_vals:
            prop_value = None
            if correct:
                prop_value = sdk_val
                if issubclass(prop_type, (int, Enum, bool)):
                    prop_value = int(sdk_val)
                prop_value = prop_type(prop_value)

            yield prop, param, prop_type, sdk_val, prop_value


class TestDaylightSavingMomentMode1:
    def test_init__should_initialize_attributes(self):
        obj = DaylightSavingMomentMode1(2, 4, 15, 35)

        assert obj.month == 2
        assert obj.day == 4
        assert obj.hour == 15
        assert obj.minute == 35

    @pytest.mark.parametrize('init_kwargs', (
        {'month': 13, 'day': 4, 'hour': 15, 'minute': 35},
        {'month': 0, 'day': 4, 'hour': 15, 'minute': 35},
        {'month': 2, 'day': 32, 'hour': 15, 'minute': 35},
        {'month': 2, 'day': 0, 'hour': 15, 'minute': 35},
        {'month': 2, 'day': 4, 'hour': -1, 'minute': 35},
        {'month': 2, 'day': 4, 'hour': 24, 'minute': 35},
        {'month': 2, 'day': 4, 'hour': 15, 'minute': -1},
        {'month': 2, 'day': 4, 'hour': 15, 'minute': 60},
    ))
    def test_init__if_parameters_out_of_range__should_raise_error(self, init_kwargs):
        with pytest.raises(ValueError):
            _ = DaylightSavingMomentMode1(**init_kwargs)

    def test_str__should_return_string_representation(self):
        obj = DaylightSavingMomentMode1(2, 4, 15, 35)

        assert str(obj) == '2-4-15-35'

    def test_repr__should_return_name_of_class(self):
        obj = DaylightSavingMomentMode1(2, 4, 15, 35)

        assert repr(obj).startswith('DaylightSavingMomentMode1(')


class TestDaylightSavingMomentMode2:
    def test_init__should_initialize_attributes(self):
        sdk = Mock()
        obj = DaylightSavingMomentMode2(sdk, True, 4096)

        assert obj._sdk is sdk
        assert obj.is_daylight is True
        assert obj.buffer_size == 4096

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(daylight_saving_mode2_properties, correct=True)
    )
    @pytest.mark.parametrize('is_daylight,param_idx', ((True, 0), (False, 1)))
    def test_read_readwrite_property__should_return_value_of_correct_type(
            self, prop, param, prop_type, sdk_value, prop_value, is_daylight, param_idx
    ):
        sdk = Mock()
        param = param[param_idx]
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DaylightSavingMomentMode2(sdk, is_daylight, 4096)

        res = getattr(obj, prop)

        sdk.get_device_param.assert_called_once_with((param, ), 4096)
        assert type(res) == prop_type
        assert res == prop_value

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(daylight_saving_mode2_properties, correct=False)
    )
    @pytest.mark.parametrize('is_daylight,param_idx', ((True, 0), (False, 1)))
    def test_read_readwrite_property__if_wrong_value_returned__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value, is_daylight, param_idx
    ):
        sdk = Mock()
        param = param[param_idx]
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DaylightSavingMomentMode2(sdk, is_daylight, 4096)

        with pytest.raises(TypeError, ValueError):
            _ = getattr(obj, prop)

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(daylight_saving_mode2_properties, correct=True)
    )
    @pytest.mark.parametrize('is_daylight,param_idx', ((True, 0), (False, 1)))
    def test_write_readwrite_property__should_set_value_on_a_device(
            self, prop, param, prop_type, sdk_value, prop_value, is_daylight, param_idx
    ):
        sdk = Mock()
        param = param[param_idx]
        sdk.set_device_param.return_value = None
        obj = DaylightSavingMomentMode2(sdk, is_daylight, 4096)

        setattr(obj, prop, prop_value)

        sdk.set_device_param.assert_called_once_with({param: sdk_value})

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(daylight_saving_mode2_properties, correct=False)
    )
    @pytest.mark.parametrize('is_daylight,param_idx', ((True, 0), (False, 1)))
    def test_write_readwrite_property__if_wrong_value_passed__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value, is_daylight, param_idx
    ):
        sdk = Mock()
        param = param[param_idx]
        sdk.set_device_param.return_value = None
        obj = DaylightSavingMomentMode2(sdk, is_daylight, 4096)

        with pytest.raises(TypeError):
            setattr(obj, prop, prop_value)

    def test_str__should_return_name_of_class(self):
        obj = DaylightSavingMomentMode1(2, 4, 15, 35)

        assert str(obj).startswith('DaylightSavingMomentMode2(')

    def test_repr__should_return_name_of_class(self):
        obj = DaylightSavingMomentMode1(2, 4, 15, 35)

        assert repr(obj).startswith('DaylightSavingMomentMode2(')


class TestDeviceParameters:
    def test_init__should_fill_attributes(self):
        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)

        assert obj._sdk is sdk
        assert obj.device_model == ZK400

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_only, correct=True)
    )
    def test_read_readonly_property__should_return_value_of_correct_type(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DeviceParameters(sdk, ZK400)

        res = getattr(obj, prop)

        sdk.get_device_param.assert_called_once_with((param, ), 4096)
        assert type(res) == prop_type
        assert res == prop_value

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_only, correct=False)
    )
    def test_read_readonly_property__if_wrong_value_returned__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DeviceParameters(sdk, ZK400)

        with pytest.raises(TypeError, ValueError):
            _ = getattr(obj, prop)

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_only, correct=True)
    )
    def test_write_readonly_property__for_read_only_properties__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)

        with pytest.raises(AttributeError):
            setattr(obj, prop, sdk_value)

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_write, correct=True)
    )
    def test_read_readwrite_property__should_return_value_of_correct_type(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DeviceParameters(sdk, ZK400)

        res = getattr(obj, prop)

        sdk.get_device_param.assert_called_once_with((param, ), 4096)
        assert type(res) == prop_type
        assert res == prop_value

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_write, correct=False)
    )
    def test_read_readwrite_property__if_wrong_value_returned__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DeviceParameters(sdk, ZK400)

        with pytest.raises(TypeError, ValueError):
            _ = getattr(obj, prop)

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_write, correct=True)
    )
    def test_write_readwrite_property__should_set_value_on_a_device(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DeviceParameters(sdk, ZK400)

        setattr(obj, prop, prop_value)

        sdk.set_device_param.assert_called_once_with({param: sdk_value})

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(device_params_read_write, correct=False)
    )
    def test_write_readwrite_property__if_wrong_value_passed__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value
    ):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DeviceParameters(sdk, ZK400)

        with pytest.raises(TypeError):
            setattr(obj, prop, prop_value)

    def test_write_reboot_writeonly_prop__if_write_1__should_set_value_on_a_device(self):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DeviceParameters(sdk, ZK400)

        obj.reboot = 1

        sdk.set_device_param.assert_called_once_with({'Reboot': '1'})

    @pytest.mark.parametrize('value', (0, '1', True, False, [], ''))
    def test_write_reboot_writeonly_prop__if_write_wrong_value__should_raise_error(self, value):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DeviceParameters(sdk, ZK400)

        with pytest.raises(TypeError):
            obj.reboot = value

    def test_read_reboot_writeonly_prop__should_raise_error(self):
        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)

        with pytest.raises(AttributeError):
            _ = obj.reboot

    def test_read_spring_daylight_time_mode2_prop__should_return_object(self):
        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)

        res = obj.spring_daylight_time_mode2

        sdk.get_device_param.assert_not_called()
        assert type(res) == DaylightSavingMomentMode2
        assert res._sdk is sdk
        assert res.is_daylight is True
        assert res.buffer_size == 4096

    def test_write_spring_daylight_time_mode2_prop__should_copy_all_fields_to_a_device(self):
        def se(params, bufsize):
            return {
                'WeekOfMonth1': 2,
                'WeekOfMonth2': 3,
                'WeekOfMonth3': 4,
                'WeekOfMonth4': 5,
                'WeekOfMonth5': 6,
                'WeekOfMonth6': 7,
                'WeekOfMonth7': 8,
                'WeekOfMonth8': 9,
                'WeekOfMonth9': 10,
                'WeekOfMonth10': 11,
            }[params]

        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)
        sdk2 = Mock()
        sdk2.get_device_param.side_effect = se
        test_obj = DaylightSavingMomentMode2(sdk2, True, 4096)

        obj.spring_daylight_time_mode2 = test_obj

        sdk.set_device_param.assert_has_calls(
            call({'WeekOfMonth1': 2}),
            call({'WeekOfMonth2': 3}),
            call({'WeekOfMonth3': 4}),
            call({'WeekOfMonth4': 5}),
            call({'WeekOfMonth5': 6}),
        )

    def test_read_fall_daylight_time_mode2_prop__should_return_object(self):
        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)

        res = obj.fall_daylight_time_mode2

        sdk.get_device_param.assert_not_called()
        assert type(res) == DaylightSavingMomentMode2
        assert res._sdk is sdk
        assert res.is_daylight is False
        assert res.buffer_size == 4096

    def test_write_fall_daylight_time_mode2_prop__should_copy_all_fields_to_a_device(self):
        def se(params, bufsize):
            return {
                'WeekOfMonth1': 2,
                'WeekOfMonth2': 3,
                'WeekOfMonth3': 4,
                'WeekOfMonth4': 5,
                'WeekOfMonth5': 6,
                'WeekOfMonth6': 7,
                'WeekOfMonth7': 8,
                'WeekOfMonth8': 9,
                'WeekOfMonth9': 10,
                'WeekOfMonth10': 11,
            }[params]

        sdk = Mock()
        obj = DeviceParameters(sdk, ZK400)
        sdk2 = Mock()
        sdk2.get_device_param.side_effect = se
        test_obj = DaylightSavingMomentMode2(sdk2, False, 4096)

        obj.fall_daylight_time_mode2 = test_obj

        sdk.set_device_param.assert_has_calls(
            call({'WeekOfMonth6': 7}),
            call({'WeekOfMonth7': 8}),
            call({'WeekOfMonth8': 9}),
            call({'WeekOfMonth9': 10}),
            call({'WeekOfMonth10': 11}),
        )

    def test_read_datetime_prop__should_correctly_calculate_datetime(self):
        sdk = Mock()
        sdk.get_device_param.return_value = {'Datetime': '347748895'}
        obj = DeviceParameters(sdk, ZK400)

        res = obj.datetime

        assert res == datetime(2010, 10, 26, 20, 54, 55)

    def test_write_datetime_prop__should_correctly_calculate_datetime(self):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DeviceParameters(sdk, ZK400)

        obj.datetime = datetime(2010, 10, 26, 20, 54, 55)

        sdk.set_device_param.assert_called_once_with({'Datetime': '347748895'})


class TestDoorParameters:
    def test_init__should_fill_attributes(self):
        sdk = Mock()
        obj = DoorParameters(sdk, ZK400, 2)

        assert obj._sdk is sdk
        assert obj.device_model == ZK400
        assert obj.door_number == 2

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(door_params_read_write, correct=True)
    )
    @pytest.mark.parametrize('door_number,param_prefix', (
        (0, 'Door1'),
        (1, 'Door2'),
        (2, 'Door3'),
        (3, 'Door4'),
    ))
    def test_read_readwrite_property__should_return_value_of_correct_type(
            self, prop, param, prop_type, sdk_value, prop_value, door_number, param_prefix
    ):
        sdk = Mock()
        full_param = param_prefix + param
        sdk.get_device_param.return_value = {full_param: sdk_value}
        obj = DoorParameters(sdk, ZK400, door_number)

        res = getattr(obj, prop)

        sdk.get_device_param.assert_called_once_with((full_param, ), 4096)
        assert type(res) == prop_type
        assert res == prop_value

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(door_params_read_write, correct=False)
    )
    @pytest.mark.parametrize('door_number,param_prefix', (
        (0, 'Door1'),
        (1, 'Door2'),
        (2, 'Door3'),
        (3, 'Door4'),
    ))
    def test_read_readwrite_property__if_wrong_value_returned__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value, door_number, param_prefix
    ):
        sdk = Mock()
        sdk.get_device_param.return_value = {param: sdk_value}
        obj = DoorParameters(sdk, ZK400, door_number)

        with pytest.raises(TypeError, ValueError):
            _ = getattr(obj, prop)

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(door_params_read_write, correct=True)
    )
    @pytest.mark.parametrize('door_number,param_prefix', (
        (0, 'Door1'),
        (1, 'Door2'),
        (2, 'Door3'),
        (3, 'Door4'),
    ))
    def test_write_readwrite_property__should_set_value_on_a_device(
            self, prop, param, prop_type, sdk_value, prop_value, door_number, param_prefix
    ):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DoorParameters(sdk, ZK400, door_number)
        full_param = param_prefix + param

        setattr(obj, prop, prop_value)

        sdk.set_device_param.assert_called_once_with({full_param: sdk_value})

    @pytest.mark.parametrize(
        'prop,param,prop_type,sdk_value,prop_value',
        get_test_combinations(door_params_read_write, correct=False)
    )
    @pytest.mark.parametrize('door_number,param_prefix', (
        (0, 'Door1'),
        (1, 'Door2'),
        (2, 'Door3'),
        (3, 'Door4'),
    ))
    def test_write_readwrite_property__if_wrong_value_passed__should_raise_error(
            self, prop, param, prop_type, sdk_value, prop_value, door_number, param_prefix
    ):
        sdk = Mock()
        sdk.set_device_param.return_value = None
        obj = DoorParameters(sdk, ZK400, door_number)

        with pytest.raises(TypeError):
            setattr(obj, prop, prop_value)
