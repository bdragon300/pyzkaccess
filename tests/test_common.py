from copy import copy, deepcopy
from datetime import datetime, time, date

import pytest

from pyzkaccess.common import DocValue, DocDict, ZKDatetimeUtils


class TestDocValue:
    @pytest.mark.parametrize('init_val', (123, '321'))
    def test_init__should_set_value_and_doc(self, init_val):
        docstr = 'test doc'

        obj = DocValue(init_val, docstr)

        assert obj.value is init_val
        assert obj.doc == docstr

    @pytest.mark.parametrize('init_val', (123, '321'))
    def test_object_interface__should_act_as_initial_value(self, init_val):
        docstr = 'test doc'

        obj = DocValue(init_val, docstr)

        assert obj == init_val
        assert isinstance(obj, init_val.__class__)
        assert repr(obj) == repr(init_val)

    @pytest.mark.parametrize('init_val', (None, (), [], object, type))
    def test_init__if_wrong_value_type_was_passed__should_raise_error(self, init_val):
        with pytest.raises(TypeError):
            DocValue(init_val, 'doc')  # noqa

    @pytest.mark.parametrize('init_val', (123, '321'))
    def test_copy__should_return_different_object(self, init_val):
        docstr = 'test doc'
        obj = DocValue(init_val, docstr)

        copied = copy(obj)

        assert copied.value == init_val
        assert copied.doc == docstr
        assert copied is not obj

    @pytest.mark.parametrize('init_val', (123, '321'))
    def test_deepcopy__should_return_different_object(self, init_val):
        docstr = 'test doc'
        obj = DocValue(init_val, docstr)

        copied = deepcopy(obj)

        assert copied.value == init_val
        assert copied.doc == docstr
        assert copied is not obj


class TestDocDict:
    def test_init__should_get_initialized_by_docvalue_documented_instances(self):
        obj = DocDict({1: 'first value', '2': 'second value'})

        assert obj[1] == 1
        assert obj[1].__doc__ == 'first value'
        assert type(obj[1]) == DocValue
        assert obj['2'] == '2'
        assert obj['2'].__doc__ == 'second value'
        assert type(obj['2']) == DocValue
        assert obj.keys() == {1, '2'}


class TestZKDatetimeUtils:
    @pytest.mark.parametrize('value,expect', (
        (347748895, datetime(2010, 10, 26, 20, 54, 55)),
        ('347748895', datetime(2010, 10, 26, 20, 54, 55)),
        (0, datetime(2000, 1, 1, 0, 0, 0)),
        ('0', datetime(2000, 1, 1, 0, 0, 0)),
        (1, datetime(2000, 1, 1, 0, 0, 1)),
        ('1', datetime(2000, 1, 1, 0, 0, 1)),
    ))
    def test_zkctime_to_datetime__should_convert_datetime(self, value, expect):
        assert ZKDatetimeUtils.zkctime_to_datetime(value) == expect

    def test_zkctime_to_datetime__if_value_is_negative__should_raise_error(self):
        with pytest.raises(ValueError):
            ZKDatetimeUtils.zkctime_to_datetime(-1)

    @pytest.mark.parametrize('value,expect', (
        (datetime(2010, 10, 26, 20, 54, 55), 347748895),
        (datetime(2000, 1, 1, 0, 0, 0), 0),
        (datetime(2000, 1, 1, 0, 0, 1), 1),
    ))
    def test_datetime_to_zkctime__should_convert_datetime(self, value, expect):
        assert ZKDatetimeUtils.datetime_to_zkctime(value) == expect

    def test_datetime_to_zkctime__if_date_less_than_2000_year__should_raise_error(self):
        with pytest.raises(ValueError):
            ZKDatetimeUtils.datetime_to_zkctime(datetime(1999, 12, 31, 23, 59, 59))

    @pytest.mark.parametrize('value,expect', (
        ('2000-02-02 15:09:10', datetime(2000, 2, 2, 15, 9, 10)),
        ('1999-12-31 23:59:59', datetime(1999, 12, 31, 23, 59, 59))
    ))
    def test_time_string_to_datetime__should_convert_datetime(self, value, expect):
        assert ZKDatetimeUtils.time_string_to_datetime(value) == expect

    @pytest.mark.parametrize('value', ('asdf', '', '2000-02-02 15:09:', 0))
    def test_time_string_to_datetime__if_value_is_invalid__should_raise_error(self, value):
        with pytest.raises(ValueError, TypeError):
            ZKDatetimeUtils.time_string_to_datetime(value)

    @pytest.mark.parametrize('value,expect', (
        (54396110, (time(8, 30), time(12, 30))),
        ('54396110', (time(8, 30), time(12, 30))),
        (0, (time(0, 0), time(0, 0))),
        ('0', (time(0, 0), time(0, 0))),
    ))
    def test_zktimerange_to_times__should_convert_to_time_ranges(self, value, expect):
        assert ZKDatetimeUtils.zktimerange_to_times(value) == expect

    def test_zktimerange_to_times__if_value_less_that_zero__should_raise_error(self):
        with pytest.raises(ValueError):
            ZKDatetimeUtils.zktimerange_to_times(-1)

    @pytest.mark.parametrize('value,expect', (
        ((time(8, 30), time(12, 30)), 54396110),
        ((time(0, 0), time(0, 0)), 0),
        ((datetime(2020, 4, 12, 8, 30), time(12, 30)), 54396110),
        ((time(0, 0), datetime(2020, 4, 12, 0, 0)), 0),
    ))
    def test_times_to_zktimerange__should_convert_to_zktimerange(self, value, expect):
        assert ZKDatetimeUtils.times_to_zktimerange(*value) == expect

    def test_zkdate_to_date__should_convert_to_date(self):
        assert ZKDatetimeUtils.zkdate_to_date('20200412') == date(2020, 4, 12)

    @pytest.mark.parametrize('value', ('0', '', 0, None))
    def test_zkdate_to_date__on_bad_value__should_raise_error(self, value):
        with pytest.raises(ValueError, TypeError):
            ZKDatetimeUtils.zkdate_to_date(value)

    @pytest.mark.parametrize('value', (date(2020, 4, 12), datetime(2020, 4, 12)))
    def test_date_to_zkdate__should_convert_to_zkdate(self, value):
        assert ZKDatetimeUtils.date_to_zkdate(value) == '20200412'
