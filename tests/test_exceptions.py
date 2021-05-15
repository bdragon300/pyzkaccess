import pytest

from pyzkaccess.exceptions import ZKSDKError


class TestZKSDKError:
    def test_init__should_initialize_right_parameters(self):
        obj = ZKSDKError('my message', -5)

        assert obj.msg == 'my message'
        assert obj.err == -5

    @pytest.mark.parametrize('errno,description', (
        (-5, 'SDK error -5: The length of the read data is not correct'),
        (10066, 'WINSOCK error 10066: WSAENOTEMPTY (Directory not empty. Cannot remove a directory that is not empty)'),
        (100500, 'Unknown error 100500'),
        (-9000, 'Unknown error -9000'),
    ))
    def test_str__should_return_error_description_and_message(self, errno, description):
        expect = 'my message: {}'.format(description)
        obj = ZKSDKError('my message', errno)

        assert str(obj) == expect
