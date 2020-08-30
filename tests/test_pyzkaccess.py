import datetime
from unittest.mock import patch, Mock, call

import pytest

from pyzkaccess import Event

with patch('ctypes.WinDLL', create=True):
    from pyzkaccess import ControlOperation, RelayGroup
    from pyzkaccess import ZKAccess, ZK100, ZK200, ZK400


class TestZKAccess:
    @pytest.fixture(autouse=True)
    def setUp(self):
        dllpath = 'somedll'
        with patch('ctypes.WinDLL', create=True) as m:
            self.obj = ZKAccess(dllpath)
            m.assert_called_with(dllpath)
            assert self.obj.dll_object == m.return_value

    def test_handle_prop(self):
        assert self.obj.handle is None

    def test_connstr_prop(self):
        assert self.obj.connstr is None

    def test_device_model_prop(self):
        dllpath = 'somedll'
        with patch('ctypes.WinDLL', create=True) as m:
            obj = ZKAccess(dllpath, device_model=ZK200)

            assert obj.device_model == ZK200

    def test_device_model_prop_default(self):
        assert self.obj.device_model == ZK400

    def test_connstr_prop_set_on_connect(self):
        test_connstr = 'protocol=TCP,ipaddress=10.0.3.201,port=4370,timeout=4000,passwd='

        self.obj.connect(test_connstr)

        assert self.obj.connstr == test_connstr

    def test_handle_prop_reset_on_disconnect(self):
        self.obj._handle = 12345

        self.obj.disconnect()

        assert self.obj.handle is None

    def test_connect_if_connstr_set_in_contructor(self):
        test_connstr = 'protocol=TCP,ipaddress=10.0.3.201,port=4370,timeout=4000,passwd='
        # self.obj.connect = Mock()

        with patch('ctypes.WinDLL', create=True) as m:
            obj = Mock(spec=ZKAccess)
            # obj.__init__ = Mock(wraps=ZKAccess.__init__)

            ZKAccess.__init__(obj, 'somedll', test_connstr)

        obj.connect.assert_called_once_with(test_connstr)

    def test_connect_ok(self):
        dll_connect_f = self.obj.dll_object.Connect.return_value
        connstr = 'protocol=TCP,ipaddress=10.0.3.201,port=4370,timeout=4000,passwd='

        self.obj.connect(connstr)

        self.obj.dll_object.Connect.assert_called_with(connstr)
        assert self.obj.handle == dll_connect_f

    def test_connect_fail(self):
        self.obj.dll_object.Connect.return_value = 0
        connstr = 'wrong_connection_string'

        with pytest.raises(ConnectionError):
            self.obj.connect(connstr)

        self.obj.dll_object.Connect.assert_called_with(connstr)
        assert self.obj.handle is None

    def test_repeated_connect(self):
        self.obj._handle = 12345

        with pytest.raises(RuntimeError):
            self.obj.connect('protocol=TCP,ipaddress=10.0.3.201,port=4370,timeout=4000,passwd=')

    def test_disconnect(self):
        handle = 12345
        self.obj._handle = 12345

        self.obj.disconnect()

        self.obj.dll_object.Disconnect.assert_called_with(handle)
        assert self.obj._handle is None

    def test_repeated_disconnect(self):
        self.obj._handle = None

        self.obj.disconnect()  # Skip if already disconnected

        assert self.obj.dll_object.Disconnect.call_count == 0
        assert self.obj._handle is None

    def test_context_manager(self):
        test_connstr = 'protocol=TCP,ipaddress=10.0.3.201,port=4370,timeout=4000,passwd='
        with patch('ctypes.WinDLL', create=True):
            obj = ZKAccess('somedll', connstr=test_connstr)
        obj.connect = Mock()
        obj.disconnect = Mock()
        obj._handle = None

        with obj as o:
            obj._handle = 12345
            assert o is obj
            obj.connect.assert_called_with(test_connstr)
            assert obj.disconnect.call_count == 0

        obj.disconnect.assert_called_with()

    def test_context_manager_already_connected(self):
        test_connstr = 'protocol=TCP,ipaddress=10.0.3.201,port=4370,timeout=4000,passwd='
        with patch('ctypes.WinDLL', create=True):
            obj = ZKAccess('somedll')
        obj.connect(test_connstr)
        obj.connect = Mock()
        obj.disconnect = Mock()

        with obj as o:
            assert o is obj
            assert obj.connect.call_count == 0
            assert obj.disconnect.call_count == 0

        assert obj.disconnect.call_count == 1

    @pytest.mark.parametrize('group', (RelayGroup.lock, RelayGroup.aux))
    def test_enable_relay(self, group):
        self.obj.zk_control_device = Mock()
        door = 1
        timeout = 5

        self.obj.enable_relay(group, door, timeout)

        self.obj.zk_control_device.assert_called_with(
            ControlOperation.output,
            door,
            group,
            timeout,
            0
        )

    @pytest.mark.parametrize('door,timeout', ((0, -1), (0, 256)))
    def test_enable_relay_error(self, door, timeout):
        self.obj.zk_control_device = Mock()

        with pytest.raises(ValueError):
            self.obj.enable_relay(RelayGroup.lock, door, timeout)

    @pytest.mark.parametrize('device_model', (ZK400, ZK200, ZK100))
    @pytest.mark.parametrize('timeout', (-1, 256))
    def test_enable_relay_error_by_model(self, device_model, timeout):
        self.obj.zk_control_device = Mock()
        self.obj.device_model = device_model
        door = device_model.relays + 1

        with pytest.raises(ValueError):
            self.obj.enable_relay(RelayGroup.lock, door, timeout)

    @pytest.mark.parametrize('device_model', (ZK400, ZK200, ZK100))
    @pytest.mark.parametrize('pattern', ((0, 0), (1, 0), (0, 1), (1, 1)))
    def test_enable_relay_list(self, device_model, pattern):
        self.obj.zk_control_device = Mock()
        self.obj.device_model = device_model
        timeout = 5
        l = pattern * (device_model.relays // 2)

        self.obj.enable_relay_list(l, timeout)

        calls = []
        for i in range(device_model.relays):
            door = int(device_model.relays_def[i])
            group = int(device_model.groups_def[i])
            if l[i]:
                calls.append(
                    call(
                        ControlOperation.output,
                        door,
                        group,
                        timeout,
                        0
                    )
                )
        self.obj.zk_control_device.assert_has_calls(calls, any_order=True)

    @pytest.mark.parametrize('timeout', (-1, 256))
    def test_enable_relay_list_error(self, timeout):
        self.obj.control_device = Mock()
        l = (0, ) * 8

        with pytest.raises(ValueError):
            self.obj.enable_relay_list(l, timeout)

    @pytest.mark.parametrize('device_model', (ZK400, ZK200, ZK100))
    @pytest.mark.parametrize('length_offset', (1, -1))
    def test_enable_relay_list_error_by_model(self, device_model, length_offset):
        self.obj.control_device = Mock()
        self.obj.device_model = device_model
        l = (0, ) * (8 + length_offset)
        timeout = 5

        with pytest.raises(ValueError):
            self.obj.enable_relay_list(l, timeout)

    def test_read_events_zk_params(self):
        test_data = '2017-02-09 12:37:41,0,0,1,220,2,200\r\n2017-02-09 12:37:42,0,0,1,221,2,200\r\n'
        self.obj.zk_get_rt_log = Mock()
        self.obj.zk_get_rt_log.return_value = test_data
        buf_size = 4096

        res = self.obj.read_events(buf_size)

        self.obj.zk_get_rt_log.assert_called_with(buf_size)

    def test_read_events_return_value(self):
        test_data = '2017-02-09 12:37:41,0,0,1,220,2,200\r\n2017-02-09 12:37:42,0,0,1,221,2,200\r\n'
        self.obj.zk_get_rt_log = Mock()
        self.obj.zk_get_rt_log.return_value = test_data
        *events_strs, empty = test_data.split('\r\n')
        check_data = [Event(s) for s in events_strs]
        buf_size = 4096

        res = self.obj.read_events(buf_size)

        r = list(res)
        for i in range(len(list(r))):
            for j in check_data[i].__slots__:
                assert getattr(check_data[i], j) == getattr(r[i], j)

    def test_zk_control_device(self):
        test_params = (
            ControlOperation.output,
            0,
            0,
            0,
            0,
            ''
        )
        self.obj.dll_object.ControlDevice.return_value = 0  # Success

        self.obj.zk_control_device(*test_params)

        self.obj.dll_object.ControlDevice.assert_called_with(self.obj.handle, *test_params)

    def test_zk_control_device_error(self):
        test_params = (
            ControlOperation.output,
            0,
            0,
            0,
            0,
            ''
        )
        self.obj.dll_object.ControlDevice.return_value = -1  # Some error

        with pytest.raises(RuntimeError):
            self.obj.zk_control_device(*test_params)

    def test_zk_get_rt_log(self):
        buf_size = 4096
        self.obj.dll_object.GetRTLog.return_value = 2  # Records count

        with patch('ctypes.create_string_buffer') as m:
            buf = m.return_value  # bytes type
            res = self.obj.zk_get_rt_log(buf_size)

            self.obj.dll_object.GetRTLog.assert_called_with(self.obj.handle, buf, buf_size)
            buf.value.decode.assert_called_with('utf-8')
            assert res == buf.value.decode.return_value

    def test_zk_get_rt_log_error(self):
        buf_size = 4096
        self.obj.dll_object.GetRTLog.return_value = -1  # Some error

        with patch('ctypes.create_string_buffer') as m:
            with pytest.raises(RuntimeError):
                res = self.obj.zk_get_rt_log(buf_size)


class TestZKRealtimeEvent:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.obj = Event()

    def test_constructor_without_parse(self):
        obj = Mock(spec=Event)

        Event.__init__(obj)

        assert obj.parse.call_count == 0

    def test_constructor_with_parse(self):
        test_data = '2017-02-09 12:37:34,0,0,1,221,2,200'
        obj = Mock(spec=Event)

        Event.__init__(obj, test_data)

        obj.parse.assert_called_with(test_data)

    def test_parse_normal(self):
        test_data = '2017-02-09 12:37:34,0,0,1,221,2,200'
        check_data = {
            'time': datetime.datetime.strptime('2017-02-09 12:37:34', '%Y-%m-%d %H:%M:%S'),
            'pin': '0',
            'card': '0',
            'door': '1',
            'event_type': '221',
            'entry_exit': '2',
            'verify_mode': '200'
        }

        self.obj.parse(test_data)

        for slot in self.obj.__slots__:
            assert getattr(self.obj, slot) == check_data[slot]

    @pytest.mark.parametrize('test_data', [
        '2017-02-09 12:37:34,0,0,1,221,2,200\r\n2017-02-09 12:37:35,0,0,1,220,2,200\r\n',
        '',
        '\r\n',
        '2017-02-09 12:37:34,0,0,1,221,2,200,5',
        '2017-02-09 12:37:34,0,0,1,221,2'
    ])
    def test_parse_error(self, test_data):
        with pytest.raises(ValueError):
            res = self.obj.parse(test_data)