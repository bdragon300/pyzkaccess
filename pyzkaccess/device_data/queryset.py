__all__ = [
    'QuerySet'
]

import math
from copy import copy
from typing import (
    Type,
    Union,
    Optional,
    Iterator,
    Generator,
    Mapping,
    Any,
    Sequence,
    TypeVar,
    Iterable
)

from .model import Model, Field


class QuerySet:
    """Interface to perform queries to data tables, iterate
    over results and insert/delete records in tables

    QuerySet using "fluent interface" in most of its methods. Many
    ORMs use this approach, so working with tables and records may look
    familiar.
    Example:
        records = zk.table('User').where(card='123456').only_fields('card', 'password').unread()
        for record in records:
            print(record.password)

    For table and fields you can use either objects or their names.
    For example, the following code has the same meaning as the previous
    one:
        from zkaccess.tables import User
        records = zk.table(User).where(card='123456').only_fields(User.card, User.password).unread()
        for record in records:
            print(record.password)

    Also QuerySet can do upsert/delete operations
    """
    _estimate_record_buffer = 256

    def __init__(self, sdk, table: Type[Model], buffer_size: Optional[int] = None):
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
        """Query given fields only from a table. Arguments can be
        field instances or their names

        Example:
            zk.table(Table1).only_fields('field1', Table1.field2)
        """
        qs = self.copy()
        only_fields = set()
        fields_mapping = self._table_cls.fields_mapping()
        for field in fields:
            if isinstance(field, str):
                if field not in fields_mapping.keys():
                    raise ValueError('No such field {}.{}'.format(self._table_cls.__name__, field))
                field = getattr(self._table_cls, field)

            elif isinstance(field, Field):
                reverse_mapping = {v: k for k, v in fields_mapping.items()}
                field_name = reverse_mapping.get(field.raw_name)
                if field_name is None or getattr(self._table_cls, field_name, None) is not field:
                    raise ValueError('No such field {}.{}'.format(self._table_cls.__name__, field))

            else:
                raise TypeError('Field must be either a table field object or a field name')

            only_fields.add(field)

        qs._only_fields.update(only_fields)
        return qs

    def where(self, **kwargs) -> 'QuerySet':
        """Return a new QuerySet instance with given fields filters.
        If current QuerySet already has some filters with the same
        fields as given, they will be rewritten with new values.

        Only "equal" compare operation is available.

        In example below filters will be card == '111' AND super_authorize == False:
            zk.table('User').where(card='123456').where(card='111', super_authorize=False)
        """
        if not kwargs:
            raise TypeError('Empty arguments')

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
        """Return only unread records instead of all.

        Every table on device has a pointer which is set to the last
        record on each query. If no records have been inserted to
        a table since last read, the "unread" query will return
        nothing
        """
        qs = self.copy()
        qs._only_unread = True
        return qs

    _ModelArgT = TypeVar('_ModelArgT', Model, Mapping[str, Any])

    def upsert(self, records: Union[Sequence[_ModelArgT], _ModelArgT]) -> None:
        """Update/insert given records (or upsert) to a table.

        Every table on a device has primary key. Typically, it is "pin"
        field.

        Upsert means that when you try to upsert a record with primary
        key field which does not contain in table, then this record
        will be inserted. Otherwise it will be updated.

        Examples:
            zk.table(User).upsert({'pin': '0', 'card': '123456'})
            zk.table(User).upsert([{'pin': '0', 'card': '123456'}, {'pin': '1', 'card': '654321'}])
            zk.table(User).upsert(User(pin='0', card='123456'))
            zk.table(User).upsert([User(pin='0', card='123456'), User(pin='1', card='654321')])
        :param records: record dict, Model instance or a sequence
         of those
        :return: None
        """
        if not isinstance(records, (Sequence, Model, Mapping)):
            raise TypeError('Argument must be a sequence, Model or mapping')

        gen = self._sdk.set_device_data(self._table_cls.table_name)
        self._bulk_operation(gen, records)

    def delete(self, records: Union[Sequence[_ModelArgT], _ModelArgT]) -> None:
        """Delete given records from a table.

        Every table on a device has primary key. Typically, it is "pin"
        field. Deletion of record is performed by a field which is
        primary key for this table. Other fields seems are ignored.

        Examples:
            zk.table(User).delete({'pin': '0', 'card': '123456'})
            zk.table(User).delete([{'pin': '0', 'card': '123456'}, {'pin': '1', 'card': '654321'}])
            zk.table(User).delete(User(pin='0', card='123456'))
            zk.table(User).delete([User(pin='0', card='123456'), User(pin='1', card='654321')])
        :param records:
        :return: None
        """
        if not isinstance(records, (Sequence, Model, Mapping)):
            raise TypeError('Argument must be a sequence, Model or mapping')

        gen = self._sdk.delete_device_data(self._table_cls.table_name)
        self._bulk_operation(gen, records)

    def delete_all(self) -> None:
        """Make a query to a table using this QuerySet and delete all
        matched records.

        Query in example below deletes records with password='123':
            zk.table('User').where(password='123').delete_all()
        :return:
        """
        gen = self._sdk.delete_device_data(self._table_cls.table_name)
        self._bulk_operation(gen, self)

    def count(self) -> int:
        """Return just a number of records in table without considering
        filters

        Unlike len(qs) this method does not fetch data, but makes
        simple request, like `SELECT COUNT(*)` in SQL.
        """
        return self._sdk.get_device_data_count(self._table_cls.table_name)

    def _bulk_operation(self,
                        gen: Generator[None, Optional[Mapping[str, str]], None],
                        records: Union[Iterable[_ModelArgT], _ModelArgT]):
        gen.send(None)
        if isinstance(records, (Mapping, Model)):
            records = (records, )

        for record in records:
            if isinstance(record, Model):
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
        """Return a size of queryset. In order to get this size, all
        records will be preliminary fetched
        """
        # Fill out cache
        # https://stackoverflow.com/questions/37189968/how-to-have-list-consume-iter-without-calling-len
        [_ for _ in self]  # noqa

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
            # Ex: 5(count) * 70(estimated len) = 350 => buffer_size==512
            if records_count == 0:
                return
            estimated_size = self._estimate_record_buffer * records_count
            buffer_size = 2 ** math.ceil(math.log2(estimated_size))

        fields = ['*']  # Query all fields if no fields was given
        if self._only_fields:
            fields = list(sorted(f.raw_name for f in self._only_fields))

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
        if stop is not None and start >= stop:
            return

        for i in self._cache[start:stop:step]:
            yield i

        i = len(self._cache)
        while stop is None or i < stop:
            try:
                item = next(self._results_iter)
            except StopIteration:
                return
            self._cache.append(item)
            if (start is None or i >= start) and (start + i) % step == 0:
                yield item
            i += 1

    def copy(self) -> 'QuerySet':
        """Return a copy of current QuerySet with empty cache"""
        res = self.__class__(self._sdk, self._table_cls, self._buffer_size)
        res._only_fields = copy(self._only_fields)
        res._filters = copy(self._filters)
        res._only_unread = self._only_unread

        return res

    class ModelIterator(Iterator):
        """Iterator for iterating over QuerySet results"""
        def __init__(self, qs: 'QuerySet', item: Optional[Union[slice, int]] = None):
            self._qs = qs
            self._item = item
            self._start, self._stop, self._step = 0, None, 1

            if isinstance(self._item, int):
                self._start = self._item
                self._stop = self._item + 1
            if isinstance(self._item, slice):
                self._start = self._item.start or 0
                self._stop = self._item.stop
                self._step = 1 if self._item.step is None else self._item.step

            self._item_iter = None

            if self._step == 0:
                raise ValueError('slice step cannot be zero')
            if self._start and self._start < 0 \
                    or self._stop and self._stop < 0 \
                    or self._step and self._step < 0:
                raise ValueError('negative indexes or step does not supported')

        def __next__(self):
            if self._item_iter is None:
                self._item_iter = self._qs._iter_cache(self._start, self._stop, self._step)

            return self._qs._table_cls().with_raw_data(
                next(self._item_iter), dirty=False
            ).with_sdk(self._qs._sdk)

    _iterator_class = ModelIterator
