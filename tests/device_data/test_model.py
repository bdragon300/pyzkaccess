from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from enum import Enum
from unittest.mock import Mock

import pytest

from pyzkaccess.device_data.model import Field, Model, models_registry


class EnumStub(Enum):
    val1 = 123
    val2 = 456


class ModelStub(Model):
    table_name = "table1"
    incremented_field = Field("IncField", int, lambda x: int(x) + 1, lambda x: x - 1, lambda x: x > 0)
    append_foo_field = Field("FooField", str, lambda x: x + "Foo", lambda x: x[:-3], lambda x: len(x) > 0)


class TestField:
    def test_init__should_set_properties(self):
        field_datatype, get_cb, set_cb, validation_cb = Mock(), Mock(), Mock(), Mock()
        obj = Field("my_name", field_datatype, get_cb, set_cb, validation_cb)

        assert obj._raw_name == "my_name"
        assert obj._field_datatype is field_datatype
        assert obj._get_cb is get_cb
        assert obj._set_cb is set_cb
        assert obj._validation_cb is validation_cb

    def test_init__should_set_default_properties(self):
        obj = Field("my_name", str)

        assert obj._raw_name == "my_name"
        assert obj._field_datatype == str
        assert obj._get_cb is None
        assert obj._set_cb is None
        assert obj._validation_cb is None

    def test_raw_name_prop__should_return_raw_name(self):
        obj = Field("my_name", str)

        assert obj.raw_name == "my_name"

    def test_field_datatype_prop__should_return_field_datatype(self):
        obj = Field("my_name", int)

        assert obj.field_datatype == int

    def test_to_raw_value__on_all_defaults__should_return_the_same_string(self):
        obj = Field("my_name", str)

        res = obj.to_raw_value("value1")

        assert res == "value1"

    @pytest.mark.parametrize(
        "datatype,value", ((str, "123"), (int, 123), (datetime, datetime(2020, 12, 12, 12, 12, 12)), (tuple, (1, 2, 3)))
    )
    def test_to_raw_value__if_type_set__should_return_string_representation(self, datatype, value):
        obj = Field("my_name", datatype)

        res = obj.to_raw_value(value)

        assert type(res) is str and res == str(value)

    def test_to_raw_value__if_type_is_enum__should_return_its_value_string_representation(self):
        obj = Field("my_name", EnumStub)

        res = obj.to_raw_value(EnumStub.val2)

        assert res == "456"

    @pytest.mark.parametrize(
        "datatype,value,set_cb,expect",
        (
            (str, "123", int, "123"),  # str=>int=>str
            (int, 123, lambda x: x + 1, "124"),  # int=>[increment]=>str
            (datetime, datetime(2020, 12, 12, 12, 12, 12), lambda x: x.day, "12"),  # dtime=>[.day]=>str
            (tuple, ("1", "2", "3"), lambda x: "".join(x), "123"),  # tuple=>[join to string]=>str
            (Enum, EnumStub.val2, lambda x: x + 1, "457"),  # Enum=>[.value]=>[increment]=>str
        ),
    )
    def test_to_raw_value__if_set_cb_set__should_use_its_value_and_cast_to_string(
        self, datatype, value, set_cb, expect
    ):
        get_cb = Mock()
        obj = Field("my_name", datatype, get_cb, set_cb)

        res = obj.to_raw_value(value)

        assert res == expect and type(res) is type(expect)
        get_cb.assert_not_called()

    @pytest.mark.parametrize(
        "datatype,value,set_cb,expect",
        (
            (str, "123", int, "123"),  # str=>int=>str
            (int, 123, lambda x: x + 1, "124"),  # int=>[increment]=>str
            (datetime, datetime(2020, 12, 12, 12, 12, 12), lambda x: x.day, "12"),  # dtime=>[.day]=>str
            (tuple, ("1", "2", "3"), lambda x: "".join(x), "123"),  # tuple=>[join to string]=>str
            (Enum, EnumStub.val2, lambda x: x + 1, "457"),  # Enum=>[.value]=>[increment]=>str
        ),
    )
    def test_to_raw_value__if_set_cb_and_validation_cb_passed__should_return_string_of_get_cb_value(
        self, datatype, value, set_cb, expect
    ):
        get_cb = Mock()
        validation_cb = Mock(return_value=True)
        obj = Field("my_name", datatype, get_cb, set_cb, validation_cb)

        res = obj.to_raw_value(value)

        assert res == expect and type(res) is type(expect)
        get_cb.assert_not_called()
        validation_cb.assert_called_once_with(value)

    @pytest.mark.parametrize(
        "datatype,value",
        (
            (str, "123"),
            (int, 123),
            (datetime, datetime(2020, 12, 12, 12, 12, 12)),
            (tuple, (1, 2, 3)),
            (Enum, EnumStub.val2),
        ),
    )
    def test_to_raw_value__if_set_cb_and_validation_cb_failed__should_raise_error(self, datatype, value):
        get_cb = Mock()
        set_cb = Mock(return_value=555)
        validation_cb = Mock(return_value=False)
        obj = Field("my_name", datatype, get_cb, set_cb, validation_cb)

        with pytest.raises(ValueError):
            obj.to_raw_value(value)

    @pytest.mark.parametrize(
        "datatype,value", ((str, 123), (str, None), (int, "123"), (datetime, 5), (tuple, datetime.now()), (Enum, 456))
    )
    def test_to_raw_value__if_value_has_another_type__should_raise_error(self, datatype, value):
        get_cb = Mock()
        set_cb = Mock(return_value=555)
        validation_cb = Mock(return_value=False)
        obj = Field("my_name", datatype, get_cb, set_cb, validation_cb)

        with pytest.raises(TypeError):
            obj.to_raw_value(value)

    def test_to_field_value__on_all_defaults__should_return_the_same_string(self):
        obj = Field("my_name", str)

        res = obj.to_field_value("value1")

        assert res == "value1"

    @pytest.mark.parametrize(
        "datatype,value,expect", ((str, "123", "123"), (int, "123", 123), (EnumStub, 456, EnumStub.val2))
    )
    def test_to_field_value__if_type_set__should_return_value_of_this_type(self, datatype, value, expect):
        obj = Field("my_name", datatype)

        res = obj.to_field_value(value)

        assert res == expect and type(res) is type(expect)

    @pytest.mark.parametrize(
        "datatype,value,get_cb,expect",
        (
            (
                datetime,
                "2020-12-13 14:15:16",
                lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
                datetime(2020, 12, 13, 14, 15, 16),
            ),  # str=>datetime
            (tuple, "123", lambda x: tuple(x), ("1", "2", "3")),  # str=>tuple
            (EnumStub, "456", lambda x: EnumStub(int(x)), EnumStub.val2),  # str=>Enum
            (bool, "1", lambda x: bool(int(x)), True),  # str=>bool
            (bool, "0", lambda x: bool(int(x)), False),  # str=>bool
        ),
    )
    def test_to_field_value__if_get_cb_returns_value_of_datatype__should_convert_value(
        self, datatype, value, get_cb, expect
    ):
        set_cb = Mock()
        validation_cb = Mock()
        obj = Field("my_name", datatype, get_cb, set_cb, validation_cb)

        res = obj.to_field_value(value)

        assert res == expect and type(res) is type(expect)
        set_cb.assert_not_called()
        validation_cb.assert_not_called()

    @pytest.mark.parametrize(
        "datatype,value",
        ((datetime, "2020-12-13 14:15:16"), (tuple, "123"), (EnumStub, "456"), (bool, "1"), (bool, "0")),
    )
    def test_to_field_value__if_get_cb_returns_none__should_return_none(self, datatype, value):
        set_cb = Mock()
        validation_cb = Mock()
        obj = Field("my_name", datatype, lambda _: None, set_cb, validation_cb)

        res = obj.to_field_value(value)

        assert res is None
        set_cb.assert_not_called()
        validation_cb.assert_not_called()

    @pytest.mark.parametrize(
        "datatype,value,get_cb,expect",
        (
            (
                str,
                "2020-12-13 14:15:16",
                lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
                "2020-12-13 14:15:16",
            ),  # str=>datetime=>str
            (tuple, "123", lambda x: list(x), ("1", "2", "3")),  # str=>list=>tuple
            (EnumStub, "456", int, EnumStub.val2),  # str=>int=>Enum
            (bool, "1", int, True),  # str=>int=>bool
            (bool, "0", int, False),  # str=>int=>bool
        ),
    )
    def test_to_field_value__if_get_cb_returns_value_not_of_datatype__should_also_cast_to_datatype(
        self, datatype, value, get_cb, expect
    ):
        set_cb = Mock()
        validation_cb = Mock()
        obj = Field("my_name", datatype, get_cb, set_cb, validation_cb)

        res = obj.to_field_value(value)

        assert res == expect and type(res) is type(expect)
        set_cb.assert_not_called()
        validation_cb.assert_not_called()

    def test_hash__should_be_hashable(self):
        obj = Field("my_name", str)

        assert hash(obj) == hash("my_name")

    def test_get_descriptor__should_correct_field_values(self):
        obj = ModelStub().with_raw_data({"IncField": "123", "FooField": "Magic"}, False)

        assert obj._dirty is False
        assert obj.append_foo_field == "MagicFoo"
        assert obj.incremented_field == 124
        assert obj._dirty is False

    def test_get_descriptor__if_no_such_raw_field__should_return_none(self):
        obj = ModelStub().with_raw_data({"FooField": "Magic"})

        assert obj.incremented_field is None

    def test_get_descriptor__if_class_instance__should_return_itself(self):
        assert isinstance(ModelStub.incremented_field, Field)

    def test_set_descriptor__should_set_raw_data(self):
        obj = ModelStub()

        obj.append_foo_field = "WowFoo"
        obj.incremented_field = 123

        assert obj._raw_data == {"IncField": "122", "FooField": "Wow"}

    def test_set_descriptor__should_set_dirty_flag(self):
        obj = ModelStub().with_raw_data({}, False)
        assert obj._dirty is False

        obj.incremented_field = 123

        assert obj._dirty is True

    def test_set_descriptor__if_none_is_given__should_delete_field_from_raw_data(self):
        obj = ModelStub().with_raw_data({"IncField": "123", "FooField": "Magic"})

        obj.incremented_field = None

        assert obj._raw_data == {"FooField": "Magic"}

    def test_set_descriptor__should_consider_field_validation(self):
        obj = ModelStub()

        with pytest.raises(ValueError):
            obj.incremented_field = -1

    def test_set_descriptor__if_class_instance__should_do_nothing(self):
        class ModelStub2(Model):
            table_name = "test"
            field1 = Field("field", str)

        ModelStub2.field1 = "testvalue"

        assert object.__getattribute__(ModelStub2, "field1") == "testvalue"

    def test_del_descriptor__should_delete_field_from_raw_data(self):
        obj = ModelStub().with_raw_data({"IncField": "123", "FooField": "Magic"})

        del obj.incremented_field

        assert obj._raw_data == {"FooField": "Magic"}

    def test_del_descriptor__should_set_dirty_flag(self):
        obj = ModelStub().with_raw_data({"IncField": "123", "FooField": "Magic"}, False)
        assert obj._dirty is False

        del obj.incremented_field

        assert obj._dirty is True

    def test_del_descriptor__if_class_instance__should_do_nothing(self):
        class ModelStub2(Model):
            table_name = "test"
            field1 = Field("field", str)

        del ModelStub2.field1

        with pytest.raises(AttributeError):
            object.__getattribute__(ModelStub2, "field1")


class TestModelMeta:
    @pytest.fixture
    def test_registry(self):
        orig_model_registry = deepcopy(models_registry)
        models_registry.clear()

        yield models_registry

        models_registry.clear()
        models_registry.update(orig_model_registry)

    def test_metaclass__should_add_class_to_registry(self, test_registry):
        class MyModel(Model):
            table_name = "test"
            field1 = Field("FieldOne", str)

        assert test_registry == {"MyModel": MyModel}

    def test_metaclass__should_fill_fields_mapping_for_each_class(self):
        class MyModel(Model):
            table_name = "test"
            field1 = Field("FieldOne", str)
            field2 = Field("FieldTwo", str)

        class MyModel2(Model):
            table_name = "test"
            field3 = Field("FieldThree", str)
            field4 = Field("FieldFour", str)

        assert MyModel._fields_mapping == {"field1": "FieldOne", "field2": "FieldTwo"}
        assert MyModel2._fields_mapping == {"field3": "FieldThree", "field4": "FieldFour"}

    def test_metaclass__should_set_field_objects_doc_attribute(self):
        class MyModel(Model):
            table_name = "test"
            field1 = Field("FieldOne", str)
            field2 = Field("FieldTwo", int)

        assert MyModel.field1.__doc__ == "MyModel.field1"
        assert MyModel.field2.__doc__ == "MyModel.field2"

    def test_metaclass__should_set_field_object_class_var_annotation(self):
        class MyModel(Model):
            table_name = "test"
            field1 = Field("FieldOne", str)
            field2 = Field("FieldTwo", int)

        assert {"field1": str, "field2": int}.items() <= MyModel.__annotations__.items()


class TestModel:
    def test_init__should_set_default_attributes(self):
        obj = ModelStub()

        assert obj._sdk is None
        assert obj._dirty is True
        assert obj._raw_data == {}

    def test_init__if_fields_has_passed__should_initialize_raw_data_only_with_given_fields(self):
        obj = ModelStub(incremented_field=123)

        assert obj._raw_data == {"IncField": "122"}

    def test_init__if_nones_has_passed_in_fields__should_ignore_them(self):
        obj = ModelStub(incremented_field=123, append_foo_field=None)

        assert obj._raw_data == {"IncField": "122"}

    def test_init__if_unknown_fields_has_passed__should_raise_error(self):
        with pytest.raises(TypeError):
            ModelStub(incremented_field=123, unknown_field=3)

    def test_init__should_consider_fields_validation(self):
        with pytest.raises(ValueError):
            ModelStub(incremented_field=-1)

    def test_dict__should_return_fields_value(self):
        obj = ModelStub().with_raw_data({"IncField": "123", "FooField": "Magic"})

        assert obj.dict == {"incremented_field": 124, "append_foo_field": "MagicFoo"}

    def test_dict__if_no_certain_field_in_raw_data__should_return_nones(self):
        obj = ModelStub().with_raw_data({"IncField": "123"})

        assert obj.dict == {"incremented_field": 124, "append_foo_field": None}

    def test_raw_data__should_return_raw_data_appended_with_empty_string_for_absend_keys(self):
        obj = ModelStub().with_raw_data({"IncField": "123"})

        assert obj.raw_data == {"IncField": "123", "FooField": ""}

    def test_fields_mapping__should_return_fields_mapping(self):
        assert ModelStub.fields_mapping() == {"incremented_field": "IncField", "append_foo_field": "FooField"}
        assert ModelStub().fields_mapping() == {"incremented_field": "IncField", "append_foo_field": "FooField"}

    def test_delete__should_delete_current_record_and_set_dirty_flag(self, generator_sends_collector):
        items = []
        sdk = Mock()
        sdk.delete_device_data.side_effect = generator_sends_collector(items)
        obj = ModelStub().with_sdk(sdk).with_raw_data({"IncField": "123", "FooField": "Magic"}, False)
        assert obj._dirty is False

        obj.delete()

        sdk.delete_device_data.assert_called_once_with("table1")
        assert items == [{"IncField": "123", "FooField": "Magic"}, None]
        assert obj._dirty is True

    def test_delete__if_manually_created_record__should_raise_error(self):
        obj = ModelStub(incremented_field=123, append_foo_field="MagicFoo")

        with pytest.raises(TypeError):
            obj.delete()

    def test_save__should_upsert_current_record_and_reset_dirty_flag(self, generator_sends_collector):
        items = []
        sdk = Mock()
        sdk.set_device_data.side_effect = generator_sends_collector(items)
        obj = ModelStub().with_sdk(sdk).with_raw_data({"IncField": "123", "FooField": "Magic"})
        assert obj._dirty is True

        obj.save()

        sdk.set_device_data.assert_called_once_with("table1")
        assert items == [{"IncField": "123", "FooField": "Magic"}, None]
        assert obj._dirty is False

    def test_save__if_manually_created_record__should_raise_error(self):
        obj = ModelStub(incremented_field=123, append_foo_field="MagicFoo")

        with pytest.raises(TypeError):
            obj.save()

    @pytest.mark.parametrize("dirty_flag", (True, False))
    def test_with_raw_data__should_set_raw_data_and_dirty_flag(self, dirty_flag):
        obj = ModelStub().with_raw_data({"IncField": "123", "FooField": "Magic"}, dirty_flag)

        assert obj._raw_data == {"IncField": "123", "FooField": "Magic"}
        assert obj._dirty == dirty_flag

    def test_with_raw_data__should_return_self(self):
        obj = ModelStub()

        assert obj.with_raw_data({}) is obj

    def test_with_sdk__should_set_sdk(self):
        sdk = Mock()
        obj = ModelStub().with_raw_data({"A": "val1"}, False).with_sdk(sdk)

        assert obj._sdk is sdk
        assert obj._raw_data == {"A": "val1"}
        assert obj._dirty is False

    def test_with_sdk__should_return_self(self):
        obj = ModelStub()

        assert obj.with_sdk(Mock()) is obj

    def test_with_zk__should_set_sdk(self):
        zk = Mock()
        obj = ModelStub().with_raw_data({"A": "val1"}, False).with_zk(zk)

        assert obj._sdk is zk.sdk
        assert obj._raw_data == {"A": "val1"}
        assert obj._dirty is False

    def test_with_zk__should_return_self(self):
        obj = ModelStub()

        assert obj.with_zk(Mock()) is obj

    def test_eq_ne__if_raw_data_and_table_are_equal__should_return_true(self):
        obj1 = ModelStub(incremented_field=123, append_foo_field="MagicFoo")
        obj2 = ModelStub(incremented_field=123, append_foo_field="MagicFoo")

        assert obj1 == obj2
        assert not (obj1 != obj2)

    @pytest.mark.parametrize(
        "table_name,kwargs",
        (
            ("table1", {"incremented_field": 1, "append_foo_field": "Magic"}),
            ("table2", {"incremented_field": 122, "append_foo_field": "Magic"}),
            ("table2", {"incremented_field": 1, "append_foo_field": "Magic"}),
        ),
    )
    def test_eq_ne__if_raw_data_or_table_are_not_equal__should_return_false(self, table_name, kwargs):
        obj1 = ModelStub(incremented_field=123, append_foo_field="MagicFoo")
        obj2 = ModelStub(**kwargs)
        obj2.table_name = table_name

        assert obj1 != obj2
        assert not (obj1 == obj2)

    def test_repr__should_return_data_table_name_and_fields_and_their_raw_values(self):
        raw_data = OrderedDict((("IncField", "123"), ("FooField", "Magic")))
        obj = ModelStub().with_raw_data(raw_data, False)

        assert repr(obj) == "ModelStub(append_foo_field=Magic, incremented_field=123)"

    def test_repr__if_dirty_flag_is_set__should_reflect_this_fact_in_string(self):
        raw_data = OrderedDict((("IncField", "123"), ("FooField", "Magic")))
        obj = ModelStub().with_raw_data(raw_data, True)

        assert repr(obj) == "*ModelStub(append_foo_field=Magic, incremented_field=123)"
