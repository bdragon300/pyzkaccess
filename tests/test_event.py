import pytest
from ..event import ZKRealtimeEvent
import datetime
from unittest.mock import Mock


class TestZKRealtimeEvent:
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.obj = ZKRealtimeEvent()

    def test_constructor_without_parse(self):
        obj = Mock(spec=ZKRealtimeEvent)

        ZKRealtimeEvent.__init__(obj)

        assert obj.parse.call_count == 0

    def test_constructor_with_parse(self):
        test_data = '2017-02-09 12:37:34,0,0,1,221,2,200'
        obj = Mock(spec=ZKRealtimeEvent)

        ZKRealtimeEvent.__init__(obj, test_data)

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

