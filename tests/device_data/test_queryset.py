from unittest.mock import Mock, MagicMock

import pytest

from pyzkaccess.device_data.queryset import QuerySet
from pyzkaccess.device_data.model import Field, Model


class ModelStub(Model):
    table_name = 'table1'
    incremented_field = Field(
        'IncField', int, lambda x: int(x) + 1, lambda x: x - 1, lambda x: x > 0
    )
    append_foo_field = Field(
        'FooField', str, lambda x: x + 'Foo', lambda x: x[:-3], lambda x: len(x) > 0
    )


class ModelStub2(Model):
    table_name = 'table2'
    field1 = Field('Field1')
    incremented_field = Field('IncField')


class TestQuerySet:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.obj = QuerySet(self.sdk, ModelStub)

    def test_init__should_initizalize_properties(self):
        obj = QuerySet(self.sdk, ModelStub, 123)

        assert obj._sdk is self.sdk
        assert obj._table_cls is ModelStub
        assert obj._cache is None
        assert obj._results_iter is None
        assert obj._buffer_size == 123
        assert obj._only_fields == set()
        assert obj._filters == {}
        assert obj._only_unread is False

    @pytest.mark.parametrize('attr,args,kwargs', (
        ('where', (), {'incremented_field': 5}),
        ('only_fields', ('incremented_field',), {}),
        ('unread', (), {})
    ))
    def test_access_methods__should_not_trigger_sdk_until_iteration_start(self, attr, args, kwargs):
        getattr(self.obj, attr)(*args, **kwargs)

        self.sdk.get_device_data_count.assert_not_called()
        self.sdk.get_device_data.assert_not_called()

    @pytest.mark.parametrize('args,expect', (
        (('incremented_field', ), {ModelStub.incremented_field}),
        (
            ('incremented_field', 'append_foo_field'),
            {ModelStub.incremented_field, ModelStub.append_foo_field}
        ),
        ((ModelStub.incremented_field,), {ModelStub.incremented_field}),
        (
            (ModelStub.incremented_field, ModelStub.append_foo_field),
            {ModelStub.incremented_field, ModelStub.append_foo_field}
        ),
        ((), set())
    ))
    def test_only_fields__should_set_fields(self, args, expect):
        res = self.obj.only_fields(*args)

        assert res._only_fields == expect

    @pytest.mark.parametrize('args,expect', (
        (
            ('incremented_field', 'append_foo_field'),
            {ModelStub.incremented_field, ModelStub.append_foo_field}
        ),
        (('append_foo_field', ), {ModelStub.incremented_field, ModelStub.append_foo_field}),
        (
            (ModelStub.incremented_field, ModelStub.append_foo_field),
            {ModelStub.incremented_field, ModelStub.append_foo_field}
        ),
        (
            (ModelStub.append_foo_field,),
            {ModelStub.incremented_field, ModelStub.append_foo_field}
        ),
        ((), {ModelStub.incremented_field})
    ))
    def test_only_fields__on_repeated_calls__should_update_previous_fields(self, args, expect):
        res = self.obj.only_fields('incremented_field').only_fields(*args)

        assert res._only_fields == expect

    def test_only_fields__should_return_another_empty_queryset_and_not_modify_original_one(self):
        data = [{'IncField': '123', 'FooField': 'Magic'}]
        obj = self.obj.where(incremented_field=3).unread()
        obj._cache = []
        obj._results_iter = original_iter = iter(data)
        res = obj.only_fields('incremented_field')

        assert res is not obj

        assert res._sdk is self.sdk and obj._sdk is self.sdk
        assert res._table_cls is ModelStub and obj._table_cls is ModelStub
        assert res._cache is None and obj._cache == []
        assert res._results_iter is None and obj._results_iter is original_iter
        assert res._buffer_size is None and obj._buffer_size is None
        assert res._only_fields == {ModelStub.incremented_field} and obj._only_fields == set()
        assert res._filters == {'IncField': '2'} and obj._filters == {'IncField': '2'}
        assert res._only_unread is True and obj._only_unread is True

    def test_only_fields__should_call_sdk_with_right_params_on_iteration_start(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        res = list(self.obj.only_fields('incremented_field', 'append_foo_field'))

        self.sdk.get_device_data_count.assert_called_once_with('table1')
        self.sdk.get_device_data.assert_called_once_with(
            'table1', ['FooField', 'IncField'], {}, 512, False
        )

    @pytest.mark.parametrize('args', (
        (None, ),
        (Field, ModelStub.incremented_field),
    ))
    def test_only_fields__if_bad_fields_were_given__should_raise_error(self, args):
        with pytest.raises(TypeError):
            self.obj.only_fields(*args)

    @pytest.mark.parametrize('args', (
        ('incremented_field', 'unknown_field'),
        ('incremented_field', ModelStub2.field1),
        ('incremented_field', ModelStub2.incremented_field),
    ))
    def test_only_fields__if_unknown_fields_were_given__should_raise_error(self, args):
        with pytest.raises(ValueError):
            self.obj.only_fields(*args)

    @pytest.mark.parametrize('kwargs,expect', (
        ({'incremented_field': 3}, {'IncField': '2'}),
        (
            {'incremented_field': 3, 'append_foo_field': 'MagicFoo'},
            {'IncField': '2', 'FooField': 'Magic'}
        )
    ))
    def test_where__should_set_filters(self, kwargs, expect):
        res = self.obj.where(**kwargs)

        assert res._filters == expect

    @pytest.mark.parametrize('kwargs,expect', (
        ({'incremented_field': 3}, {'IncField': '2'}),
        ({'append_foo_field': 'MagicFoo'}, {'IncField': '776', 'FooField': 'Magic'}),
        (
            {'incremented_field': 3, 'append_foo_field': 'MagicFoo'},
            {'IncField': '2', 'FooField': 'Magic'}
        )
    ))
    def test_where__on_repeated_calls__should_update_previous_filters(self, kwargs, expect):
        res = self.obj.where(incremented_field=777).where(**kwargs)

        assert res._filters == expect

    def test_where__should_return_another_empty_queryset(self):
        data = [{'IncField': '123', 'FooField': 'Magic'}]
        obj = self.obj.only_fields('incremented_field').unread()
        obj._cache = []
        obj._results_iter = original_iter = iter(data)

        res = obj.where(incremented_field=3)

        assert res is not obj
        assert res._sdk is self.sdk and obj._sdk is self.sdk
        assert res._table_cls is ModelStub and obj._table_cls is ModelStub
        assert res._cache is None and obj._cache == []
        assert res._results_iter is None and obj._results_iter is original_iter
        assert res._buffer_size is None and obj._buffer_size is None
        assert res._only_fields == {ModelStub.incremented_field} \
               and obj._only_fields == {ModelStub.incremented_field}
        assert res._filters == {'IncField': '2'} and obj._filters == {}
        assert res._only_unread is True and obj._only_unread is True

    def test_where__should_call_sdk_with_right_params_on_iteration_start(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        res = list(self.obj.where(incremented_field=2, append_foo_field='MagicFoo'))

        self.sdk.get_device_data_count.assert_called_once_with('table1')
        self.sdk.get_device_data.assert_called_once_with(
            'table1', ['*'], {'IncField': '1', 'FooField': 'Magic'}, 512, False
        )

    @pytest.mark.parametrize('kwargs', (
        {'incremented_field': 3, 'unknown_field': 'value1'},
        {'unknown_field': 'value1'}
    ))
    def test_where__if_unknown_fields_were_given__should_raise_error(self, kwargs):
        with pytest.raises(TypeError):
            self.obj.where(**kwargs)

    def test_where__if_parameters_are_empty__should_raise_error(self):
        with pytest.raises(TypeError):
            self.obj.where()

    def test_unread__should_set_unread_flag(self):
        res = self.obj.unread()

        assert res._only_unread is True

    def test_unread__on_repeated_calls__should_not_be_changed_anything(self):
        res = self.obj.unread().unread()

        assert res._only_unread is True

    def test_unread__should_return_another_empty_queryset_and_not_modify_original_one(self):
        data = [{'IncField': '123', 'FooField': 'Magic'}]
        obj = self.obj.where(incremented_field=3).only_fields('incremented_field')
        obj._cache = []
        obj._results_iter = original_iter = iter(data)

        res = obj.unread()

        assert res is not obj
        assert res._sdk is self.sdk and obj._sdk is self.sdk
        assert res._table_cls is ModelStub and obj._table_cls is ModelStub
        assert res._cache is None and obj._cache == []
        assert res._results_iter is None and obj._results_iter is original_iter
        assert res._buffer_size is None and obj._buffer_size is None
        assert res._only_fields == {ModelStub.incremented_field} \
               and obj._only_fields == {ModelStub.incremented_field}
        assert res._filters == {'IncField': '2'} and obj._filters == {'IncField': '2'}
        assert res._only_unread is True and obj._only_unread is False

    def test_unread__should_call_sdk_with_right_params_on_iteration_start(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        res = list(self.obj.unread())

        self.sdk.get_device_data_count.assert_called_once_with('table1')
        self.sdk.get_device_data.assert_called_once_with('table1', ['*'], {}, 512, True)

    @pytest.mark.parametrize('data,expect', (
        (
            {'incremented_field': 123, 'append_foo_field': 'MagicFoo'},
            [{'IncField': '122', 'FooField': 'Magic'}]
        ),
        (
            [{'incremented_field': 123, 'append_foo_field': 'MagicFoo'}, {'incremented_field': 5}],
            [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        ),
        (
                ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
                [{'IncField': '122', 'FooField': 'Magic'}]
        ),
        (
            [
                ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
                ModelStub(incremented_field=5)
            ],
            [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        )
    ))
    def test_upsert__should_add_records_to_table(self, data, expect, generator_sends_collector):
        items = []
        self.sdk.set_device_data.side_effect = generator_sends_collector(items)
        self.obj.upsert(data)

        self.sdk.set_device_data.assert_called_once_with('table1')
        assert items == expect + [None]

    @pytest.mark.parametrize('data,expect', (
        ({'incremented_field': 123, 'append_foo_field': ''}, []),
        (
            [{'incremented_field': 123, 'append_foo_field': 'MagicFoo'}, {'incremented_field': -1}],
            [{'FooField': 'Magic', 'IncField': '122'}]
        )
    ))
    def test_upsert__if_validation_has_failed__should_raise_error_and_not_to_commit_changes(
            self, data, expect, generator_sends_collector
    ):
        items = []
        self.sdk.set_device_data.side_effect = generator_sends_collector(items)

        with pytest.raises(ValueError):
            self.obj.upsert(data)

        assert items == expect

    @pytest.mark.parametrize('data', (
        (('incremented_field', 123), ('append_foo_field', '')),
        None,
        object(),
        0
    ))
    def test_upsert__on_bad_record_type__should_raise_error(self, data, generator_sends_collector):
        items = []
        self.sdk.set_device_data.side_effect = generator_sends_collector(items)

        with pytest.raises(TypeError):
            self.obj.upsert(data)

        assert items == []

    @pytest.mark.parametrize('data,expect', (
        (
            {'incremented_field': 123, 'append_foo_field': 'MagicFoo'},
            [{'IncField': '122', 'FooField': 'Magic'}]
        ),
        (
            [{'incremented_field': 123, 'append_foo_field': 'MagicFoo'}, {'incremented_field': 5}],
            [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        ),
        (
                ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
                [{'IncField': '122', 'FooField': 'Magic'}]
        ),
        (
            [
                ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
                ModelStub(incremented_field=5)
            ],
            [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        )
    ))
    def test_delete__should_delete_records_to_table(self, data, expect, generator_sends_collector):
        items = []
        self.sdk.delete_device_data.side_effect = generator_sends_collector(items)

        self.obj.delete(data)

        self.sdk.delete_device_data.assert_called_once_with('table1')
        assert items == expect + [None]

    @pytest.mark.parametrize('data,expect', (
        ({'incremented_field': 123, 'append_foo_field': ''}, []),
        (
            [{'incremented_field': 123, 'append_foo_field': 'MagicFoo'}, {'incremented_field': -1}],
            [{'FooField': 'Magic', 'IncField': '122'}]
        )
    ))
    def test_delete__if_validation_failed__should_raise_error_and_not_to_commit_changes(
            self, data, expect, generator_sends_collector
    ):
        items = []
        self.sdk.delete_device_data.side_effect = generator_sends_collector(items)

        with pytest.raises(ValueError):
            self.obj.delete(data)

        assert items == expect

    @pytest.mark.parametrize('data', (
        (('incremented_field', '123'), ('append_foo_field', '')),
        None,
        object(),
        0
    ))
    def test_delete__on_bad_record_type__should_raise_error(self, data, generator_sends_collector):
        items = []
        self.sdk.delete_device_data.side_effect = generator_sends_collector(items)

        with pytest.raises(TypeError):
            self.obj.delete(data)

        assert items == []

    @pytest.mark.parametrize('data', (
        [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}],
        []
    ))
    def test_delete_all__should_delete_records_from_queryset(self, data, generator_sends_collector):
        expect = data
        items = []
        self.sdk.delete_device_data.side_effect = generator_sends_collector(items)
        self.obj._cache = []
        self.obj._results_iter = iter(data)

        self.obj.delete_all()

        self.sdk.delete_device_data.assert_called_once_with('table1')
        assert items == expect + [None]

    def test_count__should_return_table_records_count_from_sdk(self):
        self.obj._cache = []
        self.obj._results_iter = MagicMock()
        self.sdk.get_device_data_count.return_value = 5

        res = self.obj.count()

        assert res == 5
        self.obj._results_iter.__next__.assert_not_called()

    def test_len__should_return_actual_size_of_queryset(self):
        raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'},
            {'FooField': 'Fast'},
            {'IncField': '422'},
            {'IncField': '522', 'FooField': 'Breath'}
        ]
        self.sdk.get_device_data_count.return_value = 5
        self.sdk.get_device_data.return_value = (x for x in raw_data)
        assert self.obj._cache is None

        res = len(self.obj)

        assert res == 5
        assert len(self.obj._cache) == 5

    def test_len__if_cache_is_fully_filled__should_return_cache_length(self):
        raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'},
            {'FooField': 'Fast'},
            {'IncField': '422'},
            {'IncField': '522', 'FooField': 'Breath'}
        ]
        self.obj._cache = raw_data
        self.obj._results_iter = MagicMock()
        self.obj._results_iter.__next__.side_effect = StopIteration

        res = len(self.obj)

        assert res == 5
        assert len(self.obj._cache) == 5
        self.sdk.get_device_data_count.assert_not_called()
        self.sdk.get_device_data.assert_not_called()

    def test_copy__should_copy_of_current_object_with_empty_cache_and_not_modify_original_one(self):
        data = [{'IncField': '123', 'FooField': 'Magic'}]
        obj = self.obj.where(incremented_field=3).only_fields('incremented_field').unread()
        obj._cache = []
        obj._results_iter = original_iter = iter(data)

        res = obj.copy()

        assert res is not obj
        assert res._sdk is self.sdk and obj._sdk is self.sdk
        assert res._table_cls is ModelStub and obj._table_cls is ModelStub
        assert res._cache is None and obj._cache == []
        assert res._results_iter is None and obj._results_iter is original_iter
        assert res._buffer_size is None and obj._buffer_size is None
        assert res._only_fields == {ModelStub.incremented_field} \
               and obj._only_fields == {ModelStub.incremented_field}
        assert res._filters == {'IncField': '2'} and obj._filters == {'IncField': '2'}
        assert res._only_unread is True and obj._only_unread is True


class TestQuerySetIterations:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.obj = QuerySet(self.sdk, ModelStub)

    def test_iteration__should_return_iterator(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        res = iter(self.obj)

        assert isinstance(res, QuerySet.ModelIterator)
        assert res._qs is self.obj
        assert res._item is None

    def test_iteration__if_table_contains_records_iterator_should_produce_model_objects(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        expect = [
            ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
            ModelStub(incremented_field=5)
        ]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        res = list(self.obj)

        assert res == expect
        self.sdk.get_device_data_count.assert_called_once_with('table1')
        self.sdk.get_device_data.assert_called_once_with('table1', ['*'], {}, 512, False)

    def test_iteration__if_table_is_empty__should_produce_no_items_and_not_to_try_get_records(self):
        data = []
        expect = []
        self.sdk.get_device_data_count.return_value = 0
        self.sdk.get_device_data.return_value = (x for x in data)

        res = list(self.obj)

        assert res == expect
        self.sdk.get_device_data_count.assert_called_once_with('table1')
        self.sdk.get_device_data.assert_not_called()

    def test_iteration__if_cache_is_not_empty__should_retrieve_items_from_there(self):
        raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'}
        ]
        expect = [
            ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
            ModelStub(incremented_field=223, append_foo_field='DangerousFoo')
        ]
        self.obj._cache = raw_data
        self.obj._results_iter = MagicMock()
        self.obj._results_iter.__next__.side_effect = StopIteration

        res = list(self.obj)

        assert res == expect
        self.sdk.get_device_data_count.assert_not_called()
        self.sdk.get_device_data.assert_not_called()

    @pytest.mark.parametrize('count,expect', (
        (1, 256),
        (5, 2048),
        (100, 32768)
    ))
    def test_iteration__should_guess_buffer_size_based_on_table_records_count(self, count, expect):
        # (get_device_data_count() * estimate_line_bytes_len) => up to twos power nearby
        # Ex: 5 * 70 = 350 => buffer_size==512
        data = [{'IncField': '122', 'FooField': 'Magic'}] * count
        self.sdk.get_device_data_count.return_value = count
        self.sdk.get_device_data.return_value = (x for x in data)
        assert self.obj._estimate_record_buffer == 256

        res = list(self.obj)

        assert len(res) == count
        self.sdk.get_device_data.assert_called_once_with('table1', ['*'], {}, expect, False)

    @pytest.mark.parametrize('count', (2, 9))
    def test_iteration__if_sdk_reports_wrong_records_count__ignore_it(self, count):
        data = [{'IncField': '122', 'FooField': 'Magic'}] * 4
        expect = [ModelStub(incremented_field=123, append_foo_field='MagicFoo')] * 4
        self.sdk.get_device_data_count.return_value = count
        self.sdk.get_device_data.return_value = (x for x in data)

        res = list(self.obj)

        assert res == expect

    def test_getitem__if_slice_passed__should_return_iterator(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        res = self.obj[:2]

        assert isinstance(res, QuerySet.ModelIterator)
        assert res._qs is self.obj
        assert res._item == slice(None, 2, None)

    @pytest.mark.parametrize('item', (
        slice(None, None),
        slice(1, 3), slice(2, 30), slice(1, None), slice(None, 3),
        slice(None, None, 2), slice(None, None, 1), slice(1, 3, 2), slice(None, 3, 2),
        slice(1, None, 2),
        0, 1, 3,
    ))
    def test_getitem__should_return_items_by_index_or_slice_and_fill_cache(self, item):
        raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'},
            {'FooField': 'Fast'},
            {'IncField': '422'},
            {'IncField': '522', 'FooField': 'Breath'}
        ]
        expect = [
            ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
            ModelStub(incremented_field=223, append_foo_field='DangerousFoo'),
            ModelStub(append_foo_field='FastFoo'),
            ModelStub(incremented_field=423),
            ModelStub(incremented_field=523, append_foo_field='BreathFoo'),
        ]
        self.sdk.get_device_data_count.return_value = 5
        self.sdk.get_device_data.return_value = (x for x in raw_data)

        if isinstance(item, slice):
            res = list(self.obj[item])
        else:
            res = self.obj[item]

        assert res == expect[item]

    def test_getitem__if_cache_is_not_empty__should_retrieve_items_from_there(self):
        raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'},
            {'FooField': 'Fast'},
            {'IncField': '422'},
            {'IncField': '522', 'FooField': 'Breath'}
        ]
        expect = [
            ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
            ModelStub(incremented_field=223, append_foo_field='DangerousFoo'),
            ModelStub(append_foo_field='FastFoo'),
            ModelStub(incremented_field=423),
            ModelStub(incremented_field=523, append_foo_field='BreathFoo'),
        ]
        self.obj._cache = raw_data
        self.obj._results_iter = MagicMock()
        self.obj._results_iter.__next__.side_effect = StopIteration

        res = list(self.obj[1:4])

        assert res == expect[1:4]
        self.sdk.get_device_data_count.assert_not_called()
        self.sdk.get_device_data.assert_not_called()

    def test_getitem__if_index_is_out_of_bounds__should_raise_error(self):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        with pytest.raises(IndexError):
            _ = self.obj[2]

    @pytest.mark.parametrize('item', (
        slice(-2, None), slice(-2, -1), slice(None, -1),
        slice(-2, None, 2), slice(-2, -1, 2), slice(None, -1, 2),
        slice(2, None, -1), slice(2, 3, -2), slice(None, 2, -2),
        slice(2, None, 0), slice(2, 3, 0), slice(None, 2, 0),
        -1, -10
    ))
    def test_getitem__if_indexes_are_negative_or_step_is_0__should_raise_error(self, item):
        data = [{'IncField': '122', 'FooField': 'Magic'}, {'IncField': '4'}]
        self.sdk.get_device_data_count.return_value = 2
        self.sdk.get_device_data.return_value = (x for x in data)

        with pytest.raises(ValueError):
            _ = self.obj[item]

    @pytest.mark.parametrize('item', (
        slice(3, 2), slice(3, 2, 2), slice(2, 2), slice(2, 2, 2)
    ))
    def test_getitem__if_start_more_or_equal_to_stop_in_slice__should_produce_nothing(self, item):
        raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'},
            {'FooField': 'Fast'},
            {'IncField': '422'},
            {'IncField': '522', 'FooField': 'Breath'}
        ]
        self.sdk.get_device_data_count.return_value = 5
        self.sdk.get_device_data.return_value = (x for x in raw_data)

        res = list(self.obj[item])

        assert res == []


class TestQuerySetModelIterator:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.sdk = Mock()
        self.qs = QuerySet(self.sdk, ModelStub)
        self.raw_data = [
            {'IncField': '122', 'FooField': 'Magic'},
            {'IncField': '222', 'FooField': 'Dangerous'},
            {'FooField': 'Fast'},
            {'IncField': '422'},
            {'IncField': '522', 'FooField': 'Breath'}
        ]
        self.data = [
            ModelStub(incremented_field=123, append_foo_field='MagicFoo'),
            ModelStub(incremented_field=223, append_foo_field='DangerousFoo'),
            ModelStub(append_foo_field='FastFoo'),
            ModelStub(incremented_field=423),
            ModelStub(incremented_field=523, append_foo_field='BreathFoo'),
        ]

    def test_next__if_cache_is_empty__should_fill_cache(self):
        expect = self.data
        self.qs._cache = []
        self.qs._results_iter = iter(self.raw_data)
        obj = QuerySet.ModelIterator(self.qs)

        res = []
        with pytest.raises(StopIteration):
            for i in range(100):
                res.append(next(obj))

        assert i == 5
        assert res == expect
        assert self.qs._cache == self.raw_data

    @pytest.mark.parametrize('item,cache_slice', (
        (slice(None, 3), slice(None, 3)),
        (slice(1, 3), slice(None, 3)),
        (slice(1, 4, 2), slice(None, 4))
    ))
    def test_next__if_cache_is_empty_and_getting_a_slice_should_fill_only_needed_items(
        self, item, cache_slice
    ):
        expect = self.data
        self.qs._cache = []
        self.qs._results_iter = iter(self.raw_data)
        obj = QuerySet.ModelIterator(self.qs, item)

        res = []
        with pytest.raises(StopIteration):
            for i in range(100):
                res.append(next(obj))

        assert res == expect[item]
        assert self.qs._cache == self.raw_data[cache_slice]

    def test_next__if_cache_is_empty_and_getting_an_item_should_fill_only_needed_items(self):
        expect = self.data
        self.qs._cache = []
        self.qs._results_iter = iter(self.raw_data)
        obj = QuerySet.ModelIterator(self.qs, 2)

        res = []
        with pytest.raises(StopIteration):
            for i in range(100):
                res.append(next(obj))

        assert len(res) == 1
        assert res[0] == expect[2]
        assert self.qs._cache == self.raw_data[:3]

    @pytest.mark.parametrize('item,cache_slice', (
        (slice(None, 1), slice(None, 3)),  # [:3] is already filled
        (slice(None, 2), slice(None, 3)),  # [:3] is already filled
        (slice(None, 4), slice(None, 4)),
        (slice(1, 2), slice(None, 3)),  # [:3] is already filled
        (slice(1, 4), slice(None, 4)),
        (slice(1, 4, 2), slice(None, 4))
    ))
    def test_next__if_cache_is_partially_filled_and_getting_a_slice__should_fill_only_needed_items(
        self, item, cache_slice
    ):
        expect = self.data
        self.qs._cache = self.raw_data[:3]
        self.qs._results_iter = iter(self.raw_data[3:])
        obj = QuerySet.ModelIterator(self.qs, item)

        res = []
        with pytest.raises(StopIteration):
            for i in range(100):
                res.append(next(obj))

        assert res == expect[item]
        assert self.qs._cache == self.raw_data[cache_slice]

    @pytest.mark.parametrize('item,cache_slice', (
        (0, slice(None, 3)),  # [:3] is already filled
        (3, slice(None, 4)),
    ))
    def test_next__if_cache_is_partially_filled_and_getting_an_item__should_fill_only_needed_items(
        self, item, cache_slice
    ):
        expect = self.data
        self.qs._cache = self.raw_data[:3]
        self.qs._results_iter = iter(self.raw_data[3:])
        obj = QuerySet.ModelIterator(self.qs, item)

        res = []
        with pytest.raises(StopIteration):
            for i in range(100):
                res.append(next(obj))

        assert len(res) == 1
        assert res[0] == expect[item]
        assert self.qs._cache == self.raw_data[cache_slice]
