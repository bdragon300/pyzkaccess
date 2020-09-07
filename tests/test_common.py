from copy import copy, deepcopy

import pytest

from pyzkaccess.common import DocValue, DocDict


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
