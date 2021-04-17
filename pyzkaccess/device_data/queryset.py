import math
from collections import namedtuple
from copy import copy
from typing import Type, Union, Optional, Iterator, Generator, Mapping, Any, Sequence, TypeVar

from .tables import DataTable, Field
from ..sdk import ZKSDK

QueryFilter = namedtuple('QueryFilter', ['field', 'operator', 'value'])


class QuerySet:
    _estimate_record_length = 256

    def __init__(self, sdk: ZKSDK, table: Type[DataTable], buffer_size: Optional[int] = None):
        self._sdk = sdk
        self._table_cls = table
        self._cache = None
        self._results_iter = None

        # Query parameters
        self._buffer_size = buffer_size
        self._only_fields = set()
        self._filters = {}
        self._only_unread = False

    def only_fields(self, *fields: Union[Field, str]) -> 'QuerySet':
        qs = self.copy()
        table_fields = set(self._table_cls._fields_mapping.keys())
        for field in fields:
            if isinstance(field, str):
                if field not in table_fields:
                    raise ValueError(
                        'No such field {}.{}'.format(self._table_cls.__name__, field)
                    )
                field = getattr(self._table_cls, field)
            elif not isinstance(field, Field):
                raise TypeError('Field must be either a table field object or a field name')

            qs._only_fields.add(field)

        return qs

    def where(self, **kwargs) -> 'QuerySet':
        if not kwargs:
            raise ValueError('Empty field expression')

        qs = self.copy()
        filters = {}
        for key, fval in kwargs.items():
            field = getattr(self._table_cls, key, None)
            if field is None:
                raise TypeError('No such field {}.{}', self._table_cls.__name__, key)
            filters[field.raw_name] = field.to_raw_value(fval)

        qs._filters.update(filters)

        return qs

    def unread(self) -> 'QuerySet':
        qs = self.copy()
        qs._only_unread = True
        return qs

    _DataTableArgT = TypeVar('_DataTableArgT', DataTable, Mapping[str, Any])

    def upsert(self, records: Union[Sequence[_DataTableArgT], _DataTableArgT]) -> None:
        if not records:
            return
        gen = self._sdk.set_device_data(self._table_cls.table_name)
        return self._bulk_operation(gen, records)

    def delete(self, records: Union[Sequence[_DataTableArgT], _DataTableArgT]):
        if not records:
            return
        gen = self._sdk.delete_device_data(self._table_cls.table_name)
        return self._bulk_operation(gen, records)

    def count(self) -> int:
        return self._sdk.get_device_data_count(self._table_cls.table_name)

    def _bulk_operation(self,
                        gen: Generator[None, Optional[Mapping[str, str]], None],
                        records: Union[Sequence[_DataTableArgT], _DataTableArgT]):
        gen.send(None)
        if isinstance(records, (Mapping, DataTable)):
            records = (records, )

        for record in records:
            if isinstance(record, DataTable):
                record = record.raw_data
            elif isinstance(record, Mapping):
                record = self._table_cls(**record).raw_data
            else:
                raise TypeError('Records must be either a data table object or a mapping')

            gen.send(record)

        try:
            gen.send(None)
        except StopIteration:
            pass

    def __iter__(self):
        if self._cache is None:
            self._fetch_data()
        return self._iterator_class(self)

    def __getitem__(self, item):
        if self._cache is None:
            self._fetch_data()

        if isinstance(item, slice):
            return self._iterator_class(self, item)

        try:
            return next(self._iterator_class(self, item))
        except StopIteration:
            raise IndexError("list index is out of range") from None

    def __len__(self):
        # https://stackoverflow.com/questions/37189968/how-to-have-list-consume-iter-without-calling-len
        [x for x in self]  # noqa
        return len(self._cache)

    def _fetch_data(self) -> None:
        self._cache = []
        self._results_iter = iter(())

        buffer_size = self._buffer_size
        if buffer_size is None:
            records_count = self._sdk.get_device_data_count(self._table_cls.table_name)
            # Get buffer size based on table records count and
            # estimated record length and round up to the nearest
            # power of 2

            # if records_count == 0:
            #     return
            buffer_size = 1024
            if records_count > 0:
                estimated_size = self._estimate_record_length * records_count
                buffer_size = 2 ** math.ceil(math.log2(estimated_size))

        fields = ['*']  # Query all fields if no fields was given
        if self._only_fields:
            fields = [f.raw_name for f in self._only_fields]

        self._results_iter = iter(self._sdk.get_device_data(
            self._table_cls.table_name,
            fields,
            self._filters,
            buffer_size,
            self._only_unread
        ))

    def _iter_cache(
            self, start: int, stop: Optional[int], step: int
    ) -> Generator[Mapping[str, Any], None, None]:
        for i in self._cache[start:stop:step]:
            yield i

        i = len(self._cache)
        while stop is None or i < stop:
            try:
                item = next(self._results_iter)
            except StopIteration:
                return
            self._cache.append(item)
            if i >= start and i % step == 0:
                yield item
            i += 1

    def copy(self) -> 'QuerySet':
        res = self.__class__(self._sdk, self._table_cls, self._buffer_size)
        res._only_fields = copy(self._only_fields)
        res._filters = copy(self._filters)
        res._only_unread = self._only_unread

        return res

    class DataTableIterator(Iterator):
        def __init__(self, qs: 'QuerySet', item: Optional[Union[slice, int]] = None):
            self._qs = qs
            self._item = item
            self._start, self._stop, self._step = 0, None, 1

            if isinstance(self._item, int):
                self._start = self._item
                self._stop = self._item + 1
            if isinstance(self._item, slice):
                # FIXME: start, stop, step < 0; step == 0; stop < start
                self._start = self._item.start or 0
                self._stop = self._item.stop
                self._step = self._item.step or 1

            self._item_iter = None

        def __next__(self):
            if self._item_iter is None:
                self._item_iter = self._qs._iter_cache(self._start, self._stop, self._step)

            return self._qs._table_cls().with_raw_data(
                next(self._item_iter), dirty=False
            ).with_sdk(self._qs._sdk)

    _iterator_class = DataTableIterator
