from unittest.mock import patch, call, ANY

import pytest

from pyzkaccess.enums import ControlOperation
from pyzkaccess.exceptions import ZKSDKError


def _alpha_sorted_keys(length, range_from, range_to):
    """Test util which returns sorted alphabetically numbers range
    as strings
    """
    return list(sorted(str(x) for x in range(length)))[range_from:range_to]


class TestZKSDK:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.dllpath = 'testdll.dll'  # noqa
        with patch('pyzkaccess.ctypes.WinDLL', create=True) as m:
            from pyzkaccess.sdk import ZKSDK

            self.t = ZKSDK(self.dllpath)  # noqa
            self.dll_mock = m.return_value

    def test_initial__should_be_disconnected(self):
        assert self.t.is_connected is False
        assert self.t.handle is None

    def test_dll__should_be_initialized_dll_object(self):
        assert self.t.dll == self.dll_mock

    @pytest.mark.parametrize('handle,expect', ((12345, True), (None, False)))
    def test_is_connected__should_return_if_connected(self, handle, expect):
        self.t.handle = handle

        assert self.t.is_connected == expect

    def test_connect__should_call_sdk(self):
        connstr = 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        expect = b'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
        self.dll_mock.Connect.return_value = 12345

        self.t.connect(connstr)

        self.dll_mock.Connect.assert_called_once_with(expect)

    def test_connect__on_success__should_keep_connected(self):
        self.dll_mock.Connect.return_value = 12345

        self.t.connect('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')

        assert self.t.handle == self.dll_mock.Connect.return_value

    @pytest.mark.parametrize('errno', (-2, 6, 997, 10013))  # SDK and WINSOCK errors
    def test_connect__on_sdk_failure__should_raise_error_with_errno(self, errno):
        self.dll_mock.Connect.return_value = 0
        self.dll_mock.PullLastError.return_value = errno

        with pytest.raises(ZKSDKError) as e:
            self.t.connect('protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd=')

        assert e.value.err == errno
        assert self.t.handle is None

    def test_disconnect__should_call_sdk(self):
        handle = 12345
        self.dll_mock.Disconnect.return_value = None
        self.t.handle = handle

        self.t.disconnect()

        self.dll_mock.Disconnect.assert_called_once_with(handle)

    def test_disconnect__should_disconnect(self):
        handle = 12345
        self.dll_mock.Disconnect.return_value = None
        self.t.handle = handle

        self.t.disconnect()

        assert self.t.handle is None

    def test_disconnect__on_repeatable_disconnect__should_do_nothing(self):
        self.dll_mock.Disconnect.return_value = None
        self.t.handle = None

        self.t.disconnect()

        assert self.t.handle is None
        self.dll_mock.Disconnect.assert_not_called()

    def test_control_device__should_call_sdk(self):
        self.t.handle = handle = 12345
        self.dll_mock.ControlDevice.return_value = 0

        self.t.control_device(ControlOperation['output'].value, 11, 22, 33, 44, 'options')

        self.dll_mock.ControlDevice.assert_called_once_with(
            handle, ControlOperation['output'].value, 11, 22, 33, 44, 'options'
        )

    def test_control_device__on_success__should_return_errno(self):
        self.t.handle = 12345
        self.dll_mock.ControlDevice.return_value = expect = 0

        res = self.t.control_device(ControlOperation['output'].value, 11, 22, 33, 44, 'options')

        assert res == expect

    def test_control_device__on_failure__should_raise_error(self):
        errno = -2
        self.t.handle = 12345
        self.dll_mock.ControlDevice.return_value = errno

        with pytest.raises(ZKSDKError) as e:
            self.t.control_device(ControlOperation['output'].value, 11, 22, 33, 44, 'options')

        assert e.value.err == errno
        assert self.t.handle is not None

    def test_get_rt_log__should_call_sdk(self):
        def se(*a, **kw):
            a[1].value = b'\r\n'
            return 0

        self.t.handle = handle = 12345
        self.dll_mock.GetRTLog.side_effect = se
        buf_size = 1024

        self.t.get_rt_log(buf_size)

        self.dll_mock.GetRTLog.assert_called_once_with(handle, ANY, buf_size)

    @pytest.mark.parametrize('buffer,expect', (
        (
            b'\r\n',
            []
        ),
        (
            b'2000-01-01 00:52:14,0,7125793,1,27,0,0\r\n',
            [
                '2000-01-01 00:52:14,0,7125793,1,27,0,0'
            ]
        ),
        (
            b'2000-01-01 00:52:14,0,7125793,1,27,0,0\r\n2000-01-01 00:53:14,0,7948905,1,27,0,0\r\n',
            [
                '2000-01-01 00:52:14,0,7125793,1,27,0,0',
                '2000-01-01 00:53:14,0,7948905,1,27,0,0'
            ]
        )
    ))
    def test_get_rt_log__on_success__should_return_event_lines(self, buffer, expect):
        def se(*a, **kw):
            a[1].value = buffer
            return 0

        self.t.handle = 12345
        self.dll_mock.GetRTLog.side_effect = se
        buf_size = 1024

        res = self.t.get_rt_log(buf_size)

        assert res == expect

    def test_get_rt_log__on_failure__raise_error(self):
        errno = -2
        buf_size = 1024
        self.t.handle = 12345
        self.dll_mock.GetRTLog.return_value = errno

        with pytest.raises(ZKSDKError) as e:
            self.t.get_rt_log(buf_size)

        assert e.value.err == errno
        assert self.t.handle is not None

    def test_search_device__should_call_sdk(self):
        def se(*a, **kw):
            a[2].value = b'\r\n'
            return 0

        broadcast_address = '192.168.1.255'
        expect_broadcast_address = b'192.168.1.255'
        self.dll_mock.SearchDevice.side_effect = se
        buf_size = 1024

        self.t.search_device(broadcast_address, buf_size)

        self.dll_mock.SearchDevice.assert_called_once_with(b'UDP', expect_broadcast_address, ANY)

    @pytest.mark.parametrize('buffer,expect', (
        (
            b'\r\n',
            []
        ),
        (
            b'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
            b'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017\r\n',
            [
                'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
                'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017'
            ]
        ),
        (
            b'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
            b'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017\r\n'
            b'MAC=00:17:61:C8:EC:18,IP=192.168.1.202,SN=DGD9190019050335135,'
            b'Device=C3-200,Ver=AC Ver 4.3.4 Apr 28 2017\r\n',
            [
                'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
                'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017',
                'MAC=00:17:61:C8:EC:18,IP=192.168.1.202,SN=DGD9190019050335135,'
                'Device=C3-200,Ver=AC Ver 4.3.4 Apr 28 2017'
            ]
        )
    ))
    def test_search_device__on_success__should_return_lines(self, buffer, expect):
        def se(*a, **kw):
            a[2].value = buffer
            return 0

        self.dll_mock.SearchDevice.side_effect = se
        buf_size = 1024

        res = self.t.search_device('192.168.1.255', buf_size)

        assert res == expect

    def test_search_device__on_failure__should_raise_error(self):
        errno = -2
        self.t.handle = 12345
        self.dll_mock.SearchDevice.return_value = errno

        with pytest.raises(ZKSDKError) as e:
            self.t.search_device('192.168.1.201', 4096)

        assert e.value.err == errno
        assert self.t.handle is not None

    @pytest.mark.parametrize('queries,query_calls', (
        (['q1'], [b'q1']),
        (
            ['q{}'.format(x) for x in range(20)],
            [','.join('q{}'.format(x) for x in range(20)).encode()],
        ),
        (
            ['q{}'.format(x) for x in range(35)],
            [
                ','.join('q{}'.format(x) for x in range(30)).encode(),
                ','.join('q{}'.format(x) for x in range(30, 35)).encode()
            ],
        ),
    ))
    def test_get_device_param__should_call_sdk_maximum_for_30_items_at_once(
            self, queries, query_calls
    ):
        def se(*a, **kw):
            res = ['{0}={0}'.format(x) for x in a[3].decode().split(',')]
            a[1].value = ','.join(res).encode() + b'\r\n'
            return 0

        self.t.handle = handle = 12345
        self.dll_mock.GetDeviceParam.side_effect = se
        buf_size = 1024

        self.t.get_device_param(queries, buf_size)

        calls = [call(handle, ANY, buf_size, q) for q in query_calls]
        self.dll_mock.GetDeviceParam.assert_has_calls(calls)

    @pytest.mark.parametrize('queries,call_buffers,expect', (
        (['q1'], [b'q1=v1'], {'q1': 'v1'}),
        (
            ['q{}'.format(x) for x in range(20)],
            [','.join('q{0}=v{0}'.format(x) for x in range(20)).encode()],
            {'q{}'.format(x): 'v{}'.format(x) for x in range(20)}
        ),
        (
            ['q{}'.format(x) for x in range(65)],
            [
                ','.join('q{0}=v{0}'.format(x) for x in range(30)).encode(),
                ','.join('q{0}=v{0}'.format(x) for x in range(30, 60)).encode(),
                ','.join('q{0}=v{0}'.format(x) for x in range(60, 65)).encode(),
            ],
            {'q{}'.format(x): 'v{}'.format(x) for x in range(65)}
        ),
    ))
    def test_get_device_param__on_success__should_return_parameters(
            self, queries, call_buffers, expect
    ):
        def se(*a, **kw):
            a[1].value = call_buffers.pop(0)
            return 0

        self.t.handle = 12345
        self.dll_mock.GetDeviceParam.side_effect = se
        buf_size = 1024

        res = self.t.get_device_param(queries, buf_size)

        assert res == expect
        assert self.t.handle is not None

    @pytest.mark.parametrize('buffer', (b'\r\n', b'q77=v77\r\n'))
    def test_get_device_param__if_sdk_returned_other_params_that_requested__raise_error(self,
                                                                                        buffer):
        def se(*a, **kw):
            a[1].value = buffer
            return 0

        self.t.handle = 12345
        self.dll_mock.GetDeviceParam.side_effect = se

        with pytest.raises(ValueError):
            self.t.get_device_param(('q1', ), 4096)

    def test_get_device_param__on_sdk_failure__raise_error(self):
        errno = -2
        self.t.handle = 12345
        self.dll_mock.GetDeviceParam.return_value = errno

        with pytest.raises(ZKSDKError) as e:
            self.t.get_device_param(('q1', ), 4096)

        assert e.value.err == errno
        assert self.t.handle is not None

    @pytest.mark.parametrize('parameters,query_calls', (
        ({'q1': 'v1'}, [b'q1=v1']),
        # NOTE: set_device_param sorts alphabetically incoming parameters
        (
            {'q{}'.format(x): 'v{}'.format(x) for x in range(15)},
            [','.join('q{0}=v{0}'.format(x) for x in _alpha_sorted_keys(15, None, None)).encode()]
        ),
        (
            {'q{}'.format(x): 'v{}'.format(x) for x in range(45)},
            [
                ','.join('q{0}=v{0}'.format(x) for x in _alpha_sorted_keys(45, 0, 20)).encode(),
                ','.join('q{0}=v{0}'.format(x) for x in _alpha_sorted_keys(45, 20, 40)).encode(),
                ','.join('q{0}=v{0}'.format(x) for x in _alpha_sorted_keys(45, 40, 45)).encode(),
            ]
        ),
    ))
    def test_set_device_param__should_call_sdk_maximum_for_20_items_at_once(
            self, parameters, query_calls
    ):
        def se(*a, **kw):
            return 0

        self.t.handle = handle = 12345
        self.dll_mock.SetDeviceParam.side_effect = se

        self.t.set_device_param(parameters)

        calls = [call(handle, q) for q in query_calls]
        self.dll_mock.SetDeviceParam.assert_has_calls(calls)

    def test_set_device_param__on_empty_parameters__should_do_nothing(self):
        self.t.handle = 12345
        self.dll_mock.GetDeviceParam.return_value = 0

        self.t.set_device_param({})

        self.dll_mock.GetDeviceParam.assert_not_called()

    def test_set_device_param__on_failure__should_raise_error(self):
        errno = -2
        self.t.handle = 12345
        self.dll_mock.SetDeviceParam.return_value = errno

        with pytest.raises(ZKSDKError) as e:
            self.t.set_device_param({'q1': 'v1'})

        assert e.value.err == errno
        assert self.t.handle is not None

    def test_object_deletion_by_gc__should_disconnect(self):
        handle = 12345
        self.dll_mock.Disconnect.return_value = None
        self.t.handle = handle

        self.t.__del__()

        self.dll_mock.Disconnect.assert_called_once_with(handle)
