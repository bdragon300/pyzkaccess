# pylint: disable=protected-access
__all__ = ["QuerySet"]

import math
from copy import copy
from typing import (
    Any,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from pyzkaccess.device_data.model import Field, Model
from pyzkaccess.sdk import ZKSDK

_ModelT = TypeVar("_ModelT", bound=Model)
_QuerySetT = TypeVar("_QuerySetT", bound="QuerySet")
RecordType = Union[Model, Mapping[str, Any]]


class QuerySet(Generic[_ModelT]):
    """Interface to make queries to data tables, iterate
    over results and write the data to tables

    QuerySet follows the "fluent interface" pattern in most of
    its methods. This means you can chain them together in a
    single line of code.

    Example::

        records = zk.table('User').where(card='123456').only_fields('card', 'password').unread()
        for record in records:
            print(record.password)

    For table and fields you can use either objects or their names.
    For example, the following is equal to the previous one::

        from zkaccess.tables import User
        records = zk.table(User).where(card='123456').only_fields(User.card, User.password).unread()
        for record in records:
            print(record.password)
    """

    _estimate_record_buffer = 256

    def __init__(self, sdk: "ZKSDK", table: Type[_ModelT], buffer_size: Optional[int] = None) -> None:
        """QuerySet constructor. Typically, you don't need to create
        QuerySet objects manually, but use `table` method of ZKAccess
        object instead.

        Args:
            sdk (ZKSDK): ZKSDK object
            table (Type[_ModelT]): model class
            buffer_size (int, optional): size of c-string buffer to
                keep query results from a device. If omitted, then
                buffer size will be guessed automatically
        """
        self._sdk = sdk
        self._table_cls = table
        self._cache: Optional[List[Mapping[str, str]]] = None
        self._results_iter: Optional[Iterator[Mapping[str, str]]] = None

        # Query parameters
        self._buffer_size = buffer_size
        self._only_fields: Set[Field] = set()
        self._filters: MutableMapping[str, str] = {}
        self._only_unread = False

    def select(self: _QuerySetT, *fields: Union[Field, str]) -> _QuerySetT:
        """Select fields to be fetched from a table. Arguments can be
        field instances or their names

        Example::

            zk.table(Table1).select('field1', Table1.field2)

        Args:
            *fields (Union[Field, str]): fields to select

        Returns:
            QuerySet: a copy of current object with new fields rule
        """
        qs: _QuerySetT = self.copy()
        only_fields = set()
        fields_mapping = self._table_cls.fields_mapping()
        for field in fields:
            if isinstance(field, str):
                if field not in fields_mapping.keys():
                    raise ValueError(f"No such field {self._table_cls.__name__}.{field}")
                field_obj = getattr(self._table_cls, field)

            elif isinstance(field, Field):
                field_obj = field
                reverse_mapping = {v: k for k, v in fields_mapping.items()}
                field_name = reverse_mapping.get(field.raw_name)
                if field_name is None or getattr(self._table_cls, field_name, None) is not field:
                    raise ValueError(f"No such field {self._table_cls.__name__}.{field}")

            else:
                raise TypeError("Field must be either a table field object or a field name")

            only_fields.add(field_obj)

        qs._only_fields.update(only_fields)
        return qs

    def only_fields(self: _QuerySetT, *fields: Union[Field, str]) -> _QuerySetT:
        """Alias for `select` method"""
        return self.select(*fields)

    def where(self: _QuerySetT, **kwargs: Any) -> _QuerySetT:
        """Add a filter to a query.

        It's similar to SQL WHERE clause. Filters in one call will be ANDed.
        Filters in repeatable calls will be ANDed as well. The same filter value
        in repeated calls will be replaced to the value in the last call.

        Supports only the equality operation due to SDK limitations.

        Here the filters will be `card == '111' AND super_authorize == False`::

            zk.table('User').where(card='123456').where(card='111', super_authorize=False)

        Args:
            **kwargs (Any): field filters

        Returns:
            QuerySet: a copy of current object with filters

        """
        if not kwargs:
            raise TypeError("Empty arguments")

        qs: _QuerySetT = self.copy()
        filters = {}
        for key, fval in kwargs.items():
            field = getattr(self._table_cls, key, None)
            if field is None:
                raise TypeError(f"No such field {self._table_cls.__name__}.{key}")
            filters[field.raw_name] = field.to_raw_value(fval)

        qs._filters.update(filters)

        return qs

    def unread(self: _QuerySetT) -> _QuerySetT:
        """Return only unread records instead of all.

        The ZK device stores a pointer to the last read record in each table.
        Once a table is read, the pointer is moved to the last record.
        We use this to track the unread records.

        Returns:
            QuerySet: a copy of current object with unread flag

        """
        qs = self.copy()
        qs._only_unread = True
        return qs

    def upsert(self, records: Union[Iterable[RecordType], RecordType]) -> None:
        """Upsert (update or insert) operation.

        Every table on a device has primary key. Typically, it is "pin"
        field.

        Upsert means that when you try to upsert a record with primary
        key value which does not contain in table, then this record
        will be inserted. Otherwise it will be updated with the data you provide.

        Examples::

            zk.table(User).upsert({'pin': '0', 'card': '123456'})
            zk.table(User).upsert([{'pin': '0', 'card': '123456'}, {'pin': '1', 'card': '654321'}])
            zk.table(User).upsert(User(pin='0', card='123456'))
            zk.table(User).upsert([User(pin='0', card='123456'), User(pin='1', card='654321')])

        Args:
            records (Union[Iterable[RecordType], RecordType]): record
                dict, Model instance or a sequence of those
        """
        if not isinstance(records, (Iterable, Model, Mapping)):
            raise TypeError("Argument must be a iterable, Model or mapping")

        gen = self._sdk.set_device_data(self._table_cls.table_name)
        self._bulk_operation(gen, records)

    def delete(self, records: Union[Iterable[RecordType], RecordType]) -> None:
        """Delete given records from a table.

        This function deletes records from a table by primary key from every
        passed record. Typically, the primary key is "pin" field.

        Examples::

            zk.table(User).delete({'pin': '0', 'card': '123456'})
            zk.table(User).delete([{'pin': '0', 'card': '123456'}, {'pin': '1', 'card': '654321'}])
            zk.table(User).delete(User(pin='0', card='123456'))
            zk.table(User).delete([User(pin='0', card='123456'), User(pin='1', card='654321')])

        Args:
            records (Union[Sequence[RecordType], RecordType]): record
                dict, Model instance or a sequence of those
        """
        if not isinstance(records, (Iterable, Model, Mapping)):
            raise TypeError("Argument must be a iterable, Model or mapping")

        gen = self._sdk.delete_device_data(self._table_cls.table_name)
        self._bulk_operation(gen, records)

    def delete_all(self) -> None:
        """Delete records satisfied to a query.

        Query in example below deletes records with `password='123'`::

            zk.table('User').where(password='123').delete_all()
        """
        gen = self._sdk.delete_device_data(self._table_cls.table_name)
        self._bulk_operation(gen, self)

    def count(self) -> int:
        """Return total count of records in the table.

        Unlike len(qs) that counts the records in a QuerySet,
        this function just returns the *total size* of records in
        device table ignoring all filters.

        This function is faster than enumerating all records,
        because it uses a special SDK call for this.

        Returns:
            int: data table size

        """
        return self._sdk.get_device_data_count(self._table_cls.table_name)

    def _bulk_operation(
        self, gen: Generator[None, Optional[Mapping[str, str]], None], records: Union[Iterable[RecordType], RecordType]
    ) -> None:
        gen.send(None)
        records_iter: Iterable[RecordType]
        if isinstance(records, (Mapping, Model)):
            records_iter = cast(Iterable[RecordType], (records,))
        else:
            records_iter = records

        for record in records_iter:
            if isinstance(record, Model):
                data = record.raw_data
            elif isinstance(record, Mapping):
                data = self._table_cls(**record).raw_data
            else:
                raise TypeError("Records must be either a data table object or a mapping")

            gen.send(data)

        try:
            gen.send(None)
        except StopIteration:
            pass

    def __iter__(self) -> Iterator[_ModelT]:
        if self._cache is None:
            self._fetch_data()
        return self._iterator_class(self)

    @overload
    def __getitem__(self, item: int) -> _ModelT: ...

    @overload
    def __getitem__(self: _QuerySetT, item: slice) -> Iterator[_ModelT]: ...

    def __getitem__(self, item: Union[int, slice]) -> Union[_ModelT, Iterator[_ModelT]]:
        if self._cache is None:
            self._fetch_data()

        if isinstance(item, slice):
            return self._iterator_class(self, item)

        try:
            return next(self._iterator_class(self, item))
        except StopIteration:
            raise IndexError("List index is out of range") from None

    def __len__(self) -> int:
        """Return a size of queryset. This operation could be slow, because
        we have to fetch the all queryset records from a device to count them.
        """
        # Fill out cache
        # https://stackoverflow.com/questions/37189968/how-to-have-list-consume-iter-without-calling-len
        [_ for _ in self]  # noqa; pylint: disable=pointless-statement,unnecessary-comprehension

        if self._cache is None:
            return 0

        return len(self._cache)

    def __bool__(self) -> bool:
        """Return True if this queryset contains any records. If query
        was not executed, fetch matched records first
        """
        return self.__len__() > 0

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

        fields = []
        if self._only_fields:
            fields = list(sorted(f.raw_name for f in self._only_fields))

        self._results_iter = iter(
            self._sdk.get_device_data(self._table_cls.table_name, fields, self._filters, buffer_size, self._only_unread)
        )

    def _iter_cache(self, start: int, stop: Optional[int], step: int) -> Generator[Mapping[str, Any], None, None]:
        if stop is not None and start >= stop:
            return

        assert self._cache is not None
        assert self._results_iter is not None
        yield from self._cache[start:stop:step]

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

    def copy(self: _QuerySetT) -> _QuerySetT:
        """Return a copy of current QuerySet with empty cache"""
        res = self.__class__(self._sdk, self._table_cls, self._buffer_size)
        res._only_fields = copy(self._only_fields)
        res._filters = copy(self._filters)
        res._only_unread = self._only_unread

        return res

    class ModelIterator(Iterator[_ModelT]):
        """Iterator for iterating over QuerySet results"""

        def __init__(self, qs: "QuerySet", item: Optional[Union[slice, int]] = None):
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

            self._item_iter: Optional[Iterator[Mapping[str, Any]]] = None

            if self._step == 0:
                raise ValueError("Slice step cannot be zero")
            # pylint: disable=too-many-boolean-expressions
            if self._start and self._start < 0 or self._stop and self._stop < 0 or self._step and self._step < 0:
                raise ValueError("Negative indexes or step does not supported")

        def __next__(self) -> _ModelT:
            if self._item_iter is None:
                self._item_iter = self._qs._iter_cache(self._start, self._stop, self._step)

            return self._qs._table_cls().with_raw_data(next(self._item_iter), dirty=False).with_sdk(self._qs._sdk)

    _iterator_class = ModelIterator
