from unittest.mock import patch

import pytest

with patch('ctypes.WinDLL', create=True):
    from pyzkaccess import ZKAccess
    from pyzkaccess.device import ZK400, ZK200, ZK100, ZKDevice
    from pyzkaccess.event import EventLog
    from pyzkaccess.door import Door, DoorList
    from pyzkaccess.relay import Relay, RelayList
    from pyzkaccess.reader import Reader, ReaderList
    from pyzkaccess.aux_input import AuxInput, AuxInputList
    from pyzkaccess.param import DeviceParameters


class TestZKAccess:
    @pytest.fixture(autouse=True)
    def setup(self):
        zksdk_patcher = patch('ZKSDK', create=True)
        self.sdk_cls = zksdk_patcher.start()
        self.sdk = self.sdk_cls.return_value
        self.connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        self.obj = ZKAccess(connstr=self.connstr)
        yield
        zksdk_patcher.stop()

    def test_init__if_no_autoconnect__should_initialize_default_attributes(self):
        assert self.obj.connstr is None
        assert self.obj.device_model == ZK400
        assert self.obj.sdk is self.sdk
        assert self.obj._device is None

    def test_init__if_no_autoconnect__should_initialize_default_event_log_attributes(self):
        assert type(self.obj._event_log) == EventLog
        assert self.obj._event_log._sdk is self.sdk
        assert self.obj._event_log.buffer_size == 4096
        assert self.obj._event_log.data.maxlen is None
        assert self.obj._event_log.only_filters == {}

    def test_init__should_call_sdk_with_given_dllpath(self):
        ZKAccess(connstr=self.connstr, dllpath='testdll')

        assert self.sdk_cls.assert_called_once_with('testdll')

    def test_init__if_device_model_is_passed__should_set_device_model_prop(self):
        obj = ZKAccess(device_model=ZK200)

        assert obj.device_model == ZK200

    def test_init__if_connstr_is_specified__should_automatically_connect(self):
        self.sdk.connect.assert_called_once_with(connstr)

    def test_init__if_device_is_specified__should_automatically_connect(self):
        device = ZKDevice(mac='00:17:61:C8:EC:17',
                          ip='192.168.1.201',
                          serial_number='DGD9190019050335134',
                          model=ZK100,
                          version='AC Ver 4.3.4 Apr 28 2017')
        expect_connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='

        _ = ZKAccess(device=device)

        self.sdk.connect.assert_called_once_with(expect_connstr)

    def test_init__if_device_is_specified__should_override_device_model(self):
        device = ZKDevice(mac='00:17:61:C8:EC:17',
                          ip='192.168.1.201',
                          serial_number='DGD9190019050335134',
                          model=ZK100,
                          version='AC Ver 4.3.4 Apr 28 2017')

        obj = ZKAccess(device=device, device_model=ZK200)

        assert obj.device_model == ZK100

    def test_init__if_both_connstr_and_device_are_specified__device_takes_precedence(self):
        device = ZKDevice(mac='00:17:61:C8:EC:17',
                          ip='192.168.1.201',
                          serial_number='DGD9190019050335134',
                          model=ZK100,
                          version='AC Ver 4.3.4 Apr 28 2017')
        test_connstr = 'protocol=TCP,ipaddress=10.0.0.23,port=4370,timeout=4000,passwd='
        expect_connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='

        _ = ZKAccess(device=device, connstr=test_connstr)

        self.sdk.connect.assert_called_once_with(expect_connstr)

    @pytest.mark.parametrize('model,doors_count', ((ZK400, 4), (ZK200, 2), (ZK100, 1)))
    def test_doors_prop__should_return_object_sequence(self, model, doors_count):
        res = self.obj.doors

        assert len(res) == doors_count
        assert type(res) == DoorList
        assert all(type(x) == Door for x in res)
        assert all(obj.number == num for obj, num in zip(res, model.doors_def))

    @pytest.mark.parametrize('model,relay_count', ((ZK400, 8), (ZK200, 4), (ZK100, 2)))
    def test_relays_prop__should_return_object_sequence(self, model, relay_count):
        res = self.obj.relays

        assert len(res) == relay_count
        assert type(res) == RelayList
        assert all(type(x) == Relay for x in res)
        assert all(obj.number == num for obj, num in zip(res, model.relays_def))
        assert all(obj.group == group for obj, group in zip(res, model.groups_def))

    @pytest.mark.parametrize('model,readers_count', ((ZK400, 4), (ZK200, 2), (ZK100, 1)))
    def test_readers_prop__should_return_object_sequence(self, model, readers_count):
        res = self.obj.readers

        assert len(res) == readers_count
        assert type(res) == ReaderList
        assert all(type(x) == Reader for x in res)
        assert all(obj.number == num for obj, num in zip(res, model.readers_def))

    @pytest.mark.parametrize('model,aux_input_count', ((ZK400, 4), (ZK200, 2), (ZK100, 1)))
    def test_aux_inputs_prop__should_return_object_sequence(self, model, aux_input_count):
        res = self.obj.aux_inputs

        assert len(res) == aux_input_count
        assert type(res) == AuxInputList
        assert all(type(x) == AuxInput for x in res)
        assert all(obj.number == num for obj, num in zip(res, model.aux_inputs_def))

    def test_events_prop__should_return_event_log(self):
        res = self.obj.events

        assert res is self.obj._event_log
        assert res.only_filters == {}

    def test_parameters_prop__should_return_object_of_device_parameters(self):
        res = self.obj.parameters

        assert type(res) == DeviceParameters
        assert res._sdk == self.sdk
        assert res.device_model == ZK200

    def test_device_prop__if_device_was_passed_to_init__should_return_it(self):
        device = ZKDevice(mac='00:17:61:C8:EC:17',
                          ip='192.168.1.201',
                          serial_number='DGD9190019050335134',
                          model=ZK100,
                          version='AC Ver 4.3.4 Apr 28 2017')
        obj = ZKAccess(device=device)

        res = obj.device

        assert res is device

    def test_device_prop__if_device_was_not_passed_to_init__should_return_new_object(self):
        def se(params, bufsize):
            return {
                'IPAddress': '10.0.0.2',
                '~SerialNumber': 'test serial'
            }[params[0]]

        self.sdk.get_device_param.side_effect = se
        connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        obj = ZKAccess(connstr=connstr, device_model=ZK200)

        res = obj.device

        assert obj._device is None
        assert type(res) == ZKDevice
        assert res.mac is None
        assert res.ip == '10.0.0.2'
        assert res.serial_number == 'test serial'
        assert res.model == ZK200
        assert res.version is None

    def test_device_prop__if_not_connected__should_raise_error(self):
        obj = ZKAccess()

        with pytest.raises(RuntimeError):
            _ = obj.device

    def test_dll_object_prop__should_return_sdk_dll_object(self):
        res = self.obj.dll_object

        assert res is self.sdk.dll

    def test_handle_prop__should_return_sdk_handle(self):
        res = self.obj.handle

        assert res is self.sdk.handle

    def test_search_devices__should_call_sdk_function(self):
        self.sdk_cls.search_devices.return_value = []

        _ = ZKAccess.search_devices('192.168.1.255')

        self.sdk.search_devices.assert_called_once_with('192.168.1.255', 4096)

    def test_search_devices__should_return_list_of_found_device_objects(self):
        self.sdk_cls.search_devices.return_value = [
            'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
            'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017',
            'MAC=00:17:61:C8:EC:18,IP=192.168.1.202,SN=DGD9190019050335135,'
            'Device=C3-200,Ver=AC Ver 4.3.4 Apr 28 2017'
        ]
        expect = (
            ZKDevice(mac='00:17:61:C8:EC:17', ip='192.168.1.201',
                     serial_number='DGD9190019050335134', model=ZK400,
                     version='AC Ver 4.3.4 Apr 28 2017'),
            ZKDevice(mac='00:17:61:C8:EC:18', ip='192.168.1.202',
                     serial_number='DGD9190019050335135', model=ZK200,
                     version='AC Ver 4.3.4 Apr 28 2017'),
        )

        res = ZKAccess.search_devices('192.168.1.255')

        assert res == expect

    def test_connect__should_call_sdk_function(self):
        connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        obj = ZKAccess()

        obj.connect(connstr)

        self.sdk.connect.assert_called_once_with(connstr)
        assert obj.connstr == connstr

    def test_connect__if_connected_and_trying_connect_with_same_connstr__should_do_nothing(self):
        self.obj.connect(self.connstr)

        self.sdk.connect.assert_not_called()
        assert self.obj.connstr == self.connstr

    def test_connect__if_connected_and_trying_connect_with_another_connstr__should_raise_error(
            self
    ):
        connstr2 = 'protocol=TCP,ipaddress=192.168.1.202,port=4370,timeout=4000,passwd='

        with pytest.raises(ValueError):
            self.obj.connect(connstr2)

    def test_disconnect__should_call_sdk_function(self):
        self.obj.disconnect()

        self.sdk.disconnect.assert_called_once_with(self.connstr)
        assert self.obj.connstr == self.connstr

    def test_restart__should_call_sdk_function(self):
        self.obj.restart()

        self.sdk.disconnect.assert_called_once_with(self.connstr)
        assert self.obj.connstr == self.connstr

    def test_context_manager__should_return_self(self):
        with self.obj as ctx_obj:
            assert ctx_obj is self.obj

    def test_context_manager__should_disconnect_after_exit(self):
        with self.obj:
            pass

        assert self.sdk.disconnect.assert_called_once_with()
