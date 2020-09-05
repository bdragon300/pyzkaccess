from unittest.mock import patch

import pytest

with patch('ctypes.WinDLL', create=True):
    from pyzkaccess.device import ZKDevice, ZK400


class TestZKDevice:
    def test_init__if_nothing_passed__should_raise_error(self):
        with pytest.raises(TypeError):
            ZKDevice()

    @pytest.mark.parametrize('device_string', (
        'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
        'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017',

        'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
        'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017\r\n',
    ))
    def test_init__if_device_string_passed__should_parse_and_fill_object_attributes(self, device_string):
        obj = ZKDevice(device_string)

        assert obj.mac == '00:17:61:C8:EC:17'
        assert obj.ip == '192.168.1.201'
        assert obj.serial_number == 'DGD9190019050335134'
        assert obj.model == ZK400
        assert obj.version == 'AC Ver 4.3.4 Apr 28 2017'

    @pytest.mark.parametrize('device_string', (
        # String is duplicated
        'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
        'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017\r\n'
        'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
        'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017',

        # Wrong model
        'MAC=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,' \
        'Device=UNKNOWN,Ver=AC Ver 4.3.4 Apr 28 2017'

        # Unknown key with equal count of keys
        'UNKNOWN=00:17:61:C8:EC:17,IP=192.168.1.201,SN=DGD9190019050335134,'
        'Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017',

        # The lack of one of keys
        'IP=192.168.1.201,SN=DGD9190019050335134,Device=C3-400,Ver=AC Ver 4.3.4 Apr 28 2017',

        # Wrong string
        'wrong_string',

        # Empty strings
        '\r\n',
        ''
    ))
    def test_init__if_device_string_is_incorrect__should_raise_error(self, device_string):
        with pytest.raises(ValueError):
            ZKDevice(device_string)

    def test_init__if_parameters_are_passed__should_set_object_attributes(self):
        obj = ZKDevice(mac='00:17:61:C8:EC:17',
                       ip='192.168.1.201',
                       serial_number='DGD9190019050335134',
                       model=ZK400,
                       version='AC Ver 4.3.4 Apr 28 2017')

        assert obj.mac == '00:17:61:C8:EC:17'
        assert obj.ip == '192.168.1.201'
        assert obj.serial_number == 'DGD9190019050335134'
        assert obj.model == ZK400
        assert obj.version == 'AC Ver 4.3.4 Apr 28 2017'

    def test_str__should_return_name_of_class(self):
        obj = ZKDevice(mac='00:17:61:C8:EC:17',
                       ip='192.168.1.201',
                       serial_number='DGD9190019050335134',
                       model=ZK400,
                       version='AC Ver 4.3.4 Apr 28 2017')

        assert str(obj).startswith('Device[C3-400](')

    def test_repr__should_return_name_of_class(self):
        obj = ZKDevice(mac='00:17:61:C8:EC:17',
                       ip='192.168.1.201',
                       serial_number='DGD9190019050335134',
                       model=ZK400,
                       version='AC Ver 4.3.4 Apr 28 2017')

        assert repr(obj).startswith('Device[C3-400](')
