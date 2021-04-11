import math
from typing import Type, Union, Optional, Iterator, Generator, Mapping, Any

from .tables import DataTable, Field
from ..sdk import ZKSDK


class ModelIterator(Iterator):
    def __init__(self, qs: 'QuerySet', item: Optional[Union[slice, int]] = None):
        self._qs = qs
        self._item = item
        self._start, self._stop, self._step = 0, None, 1

        if isinstance(self._item, int):
            self._start = self._item
            self._stop = self._item + 1
        if isinstance(self._item, slice):
            # FIXME: start, stop, step < 0; step == 0; stop < start
            self._start = self._item.start
            self._stop = self._item.stop
            self._step = self._item.step

        self._item_iter = None

    def __next__(self):
        if self._item_iter is None:
            self._item_iter = self._qs._iter_cache(self._start, self._stop, self._step)

        return self._qs._table_cls().with_raw_data(next(self._item_iter))


class QuerySet:
    _iterator_class = ModelIterator
    _estimate_record_length = 256

    def __init__(self, sdk: ZKSDK, table: Type[DataTable], buffer_size: Optional[int] = None):
        self._sdk = sdk
        self._table_cls = table
        self._cache = None
        self._results_iter = None

        # Query set parameters
        self._only_fields = set()
        self._filters = []
        self._only_unread = False
        self._buffer_size = buffer_size

    def only_fields(self, *fields: Union[Field, str]) -> 'QuerySet':
        res = self.copy()
        table_fields = set(self._table_cls._fields_mapping.keys())
        for field in fields:
            if isinstance(field, str):
                if field not in table_fields:
                    raise ValueError(
                        'Unknown field {}.{}'.format(self._table_cls.table_name, field)
                    )
                field = getattr(self._table_cls, field)
            elif not isinstance(field, Field):
                raise TypeError('Field must be either a table field object or a field name')

            res._only_fields.add(field)

        return res

    def where(self, filter_expr: Field) -> 'QuerySet':
        if not filter_expr.filters:
            raise ValueError('Empty field expression')

        res = self.copy()
        res._filters.extend(filter_expr.filters)
        return res

    def unread(self) -> 'QuerySet':
        res = self.copy()
        res._only_unread = True
        return res

    def clear_cache(self) -> 'QuerySet':
        res = self.copy()
        res._cache = None
        return res

    def __iter__(self):
        if self._cache is None:
            self._fetch_data()
        return self._iterator_class(self)

    def __getitem__(self, item):
        if self._cache is None:
            self._fetch_data()

        if isinstance(item, slice):
            return self._iterator_class(self, item)

        return next(self._iterator_class(self, item))

    def __len__(self):
        # https://stackoverflow.com/questions/37189968/how-to-have-list-consume-iter-without-calling-len
        [x for x in self]  # noqa
        return len(self._cache)

    def _fetch_data(self):
        self._cache = []
        self._results_iter = iter(())

        buffer_size = self._buffer_size
        if buffer_size is None:
            records_count = self._sdk.get_device_data_count(self._table_cls.table_name)
            # Get buffer size based on table records count and
            # estimated record length and round up to the nearest
            # power of 2
            if records_count == 0:
                return
            estimated_size = self._estimate_record_length * records_count
            buffer_size = 2 ** math.ceil(math.log2(estimated_size))

        fields = ['*']  # Query all fields if no fields was given
        if self._only_fields:
            fields = [f.name for f in self._only_fields]

        self._results_iter = iter(self._sdk.get_device_data(
            self._table_cls.table_name,
            fields,
            self._filters,
            buffer_size,
            self._only_unread
        ))

    def _iter_cache(self, start, stop, step) -> Generator[Mapping[str, Any], None, None]:
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
        return self.__class__(self._sdk, self._table_cls)  # FIXME: copy, not new!
