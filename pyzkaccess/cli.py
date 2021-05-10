import abc
import csv
import os
import re
import sys
from datetime import date, time, datetime
from enum import Enum
from typing import Type, Any, Iterable, TextIO, Mapping, Generator, Set, Union, KeysView, Optional
from unittest.mock import Mock

import fire
import prettytable
from fire.core import FireError

import pyzkaccess.ctypes_
from pyzkaccess import ZKAccess, ZK100, ZK200, ZK400
from pyzkaccess.device_data.model import models_registry, Model
from pyzkaccess.device_data.queryset import QuerySet
from pyzkaccess.door import Door
from pyzkaccess.enums import PassageDirection, VerifyMode
from pyzkaccess.param import DaylightSavingMomentMode1, DaylightSavingMomentMode2

device_models = {'ZK100': ZK100, 'ZK200': ZK200, 'ZK400': ZK400}

opt_io_format = 'csv'
data_in = sys.stdin
data_out = sys.stdout


doors_params_error = object()


class BaseFormatter(metaclass=abc.ABCMeta):
    """Base class for particular formatters"""
    class WriterInterface(metaclass=abc.ABCMeta):
        def __init__(self, ostream: TextIO, headers: list):
            self._ostream = ostream
            self._headers = headers
            self._writer = None

        @abc.abstractmethod
        def write(self, record: Mapping[str, str]) -> None:
            pass

        @abc.abstractmethod
        def flush(self) -> None:
            pass

    def __init__(self, istream: TextIO, ostream: TextIO, headers: Iterable[str]):
        self._istream = istream
        self._ostream = ostream
        self._headers = list(sorted(headers))

    @staticmethod
    def get_formatter(io_format: str) -> 'Type[BaseFormatter]':
        if io_format not in io_formats:
            raise FireError("{} format(s) are only supported", sorted(io_formats.keys()))
        return io_formats[io_format]

    @abc.abstractmethod
    def get_reader(self) -> Iterable[Mapping[str, str]]:
        pass

    @abc.abstractmethod
    def get_writer(self) -> WriterInterface:
        pass


class CSVFormatter(BaseFormatter):
    """Formatter for comma-separated values format"""
    class CSVWriter(BaseFormatter.WriterInterface):
        def write(self, record: Mapping[str, str]) -> None:
            record = {k: record.get(k) for k in self._headers}

            if self._writer is None:
                self._writer = csv.DictWriter(self._ostream, self._headers)
                self._writer.writeheader()

            self._writer.writerow(record)

        def flush(self) -> None:
            if self._writer is None:
                self._writer = csv.DictWriter(self._ostream, self._headers)
                self._writer.writeheader()

            self._ostream.flush()

    def get_reader(self) -> Iterable[Mapping[str, str]]:
        def _reader():
            for item in csv.DictReader(self._istream):
                item = {k: item[k] for k in self._headers}
                yield item

        return _reader()

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return CSVFormatter.CSVWriter(self._ostream, self._headers)


class ASCIITableFormatter(CSVFormatter):
    class ASCIITableWriter(BaseFormatter.WriterInterface):
        def write(self, record: Mapping[str, str]) -> None:
            if self._writer is None:
                self._writer = prettytable.PrettyTable(field_names=self._headers, align='l')

            record = [record.get(k) for k in self._headers]
            self._writer.add_row(record)

        def flush(self) -> None:
            if self._writer is None:
                self._writer = prettytable.PrettyTable(field_names=self._headers, align='l')

            self._ostream.write(self._writer.get_string())
            self._ostream.flush()

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return ASCIITableFormatter.ASCIITableWriter(self._ostream, self._headers)


class EventsPollFormatter(CSVFormatter):
    """Formatter special for events.poll iterative function output
    for 'ascii_table' mode
    """
    class ASCIITableWriter(BaseFormatter.WriterInterface):
        FIELD_FORMAT = '{:<15}{:<5}{:<15}{:<15}{:<5}{:<25}{:<15}'

        def write(self, record: Mapping[str, str]) -> None:
            if self._writer is None:
                self._writer = self.FIELD_FORMAT
                self._ostream.write(self._writer.format(*self._headers))
                self._ostream.write('\n')

            record = [str(record.get(k) or '') for k in self._headers]
            self._ostream.write(self._writer.format(*record))
            self._ostream.write('\n')
            self._ostream.flush()

        def flush(self) -> None:
            if self._writer is None:
                self._writer = self.FIELD_FORMAT
                self._ostream.write(self._writer.format(*self._headers))
                self._ostream.write('\n')

            self._ostream.flush()

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return EventsPollFormatter.ASCIITableWriter(self._ostream, self._headers)


io_formats = {
    'csv': CSVFormatter,
    'ascii_table': ASCIITableFormatter
}


class BaseConverter(metaclass=abc.ABCMeta):
    def __init__(self, formatter: BaseFormatter, *args, **kwargs):
        self._formatter = formatter
        self._args = args
        self._kwargs = kwargs

    @abc.abstractmethod
    def read_records(self) -> Generator[Mapping[str, Any], None, None]:
        pass

    @abc.abstractmethod
    def write_records(self, records: Iterable[Mapping[str, Any]]):
        pass


class TextConverter(BaseConverter):
    """Converter which simply prints and reads text field values without
    any transformations
    """
    def read_records(self) -> Generator[Mapping[str, Any], None, None]:
        for item in self._formatter.get_reader():
            yield item

    def write_records(self, records: Iterable[Mapping[str, Any]]):
        writer = self._formatter.get_writer()
        for item in records:
            writer.write(item)

        writer.flush()


class TypedFieldConverter(BaseConverter):
    """Converter performs text input/output for field values of any
    non-string types. Convertion does based on given field-type mapping
    """
    TUPLE_SEPARATOR = ','

    def __init__(self, formatter: BaseFormatter, field_types: Mapping[str, Type], *args, **kwargs):
        super().__init__(formatter, *args, **kwargs)
        self._field_types = field_types

        # The following converters parses string value respresentation from
        # stdin and converts to a field value
        # {type: (cast_function, error message)
        self._input_converters = {
            str: (lambda x: str(x), 'string'),
            bool: (lambda x: bool(int(x)), 'boolean, 0 or 1'),
            int: (int, 'integer'),
            tuple: (self._parse_tuple, 'comma separated values'),
            date: (
                lambda x: datetime.strptime(x, '%Y-%m-%d').date(),
                'date string, e.g. "2020-02-01"'
            ),
            time: (
                lambda x: datetime.strptime(x, '%H:%M:%S').time(),
                'time string, e.g. "07:40:00"'
            ),
            datetime: (
                lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'),
                'datetime string, e.g. "2020-02-01 07:40:00"'
            ),
            DaylightSavingMomentMode1: (
                lambda x: DaylightSavingMomentMode1.strptime(x, '%m-%d %H:%M'),
                'datetime moment, e.g. "02-01 07:40"'
            ),
            DaylightSavingMomentMode2: (
                self._parse_daylight_saving_moment_mode2,
                '7 comma-separated values, '
                '[month, week_of_month, day_of_week, hour, minute, is_daylight, buffer_size], '
                'e.g "2,1,1,7,40,1,4096"'
            )
        }

        # The following functions converts field values to their string
        # representation suitable for stdout output
        self._output_converters = {
            str: lambda x: str(x),
            bool: lambda x: str(int(x)),
            int: str,
            tuple: self._unparse_tuple,
            date: lambda x: x.strftime('%Y-%m-%d'),
            time: lambda x: x.strftime('%H:%M:%S'),
            datetime: lambda x: x.strftime('%Y-%m-%d %H:%M:%S'),
            DaylightSavingMomentMode1: lambda x: x.strftime('%m-%d %H:%M'),
            DaylightSavingMomentMode2: self._unparse_daylight_saving_moment_mode2
        }

    def read_records(self) -> Generator[Mapping[str, Any], None, None]:
        for item in self._formatter.get_reader():
            # Convert a text field value to a typed value
            yield self.to_record_dict(item)

    def write_records(self, records: Iterable[Mapping[str, Any]]):
        writer = self._formatter.get_writer()
        for item in records:
            # Convert a typed field value to a string value
            record = self.to_string_dict(item)
            writer.write(record)

        writer.flush()

    def to_record_dict(self, data: Mapping[str, str]) -> Mapping[str, Any]:
        return {fname: self._parse_value(fname, fval, self._field_types.get(fname, str))
                for fname, fval in data.items()}

    def to_string_dict(self, record: Mapping[str, Any]) -> Mapping[str, str]:
        return {fname: self._unparse_value(fval, self._field_types.get(fname, str))
                for fname, fval in record.items()}

    def _parse_value(self, field_name: str, value: str, field_datatype) -> Optional[Any]:
        if value == '':
            return None

        error_msg = ''
        try:
            if issubclass(field_datatype, Enum):
                error_msg = 'one of values: {}'.format(
                    ','.join(x for x in dir(field_datatype) if not x.startswith('_'))
                )
                return field_datatype[value]

            cast, error_msg = self._input_converters[field_datatype]
            return cast(value)
        except (ValueError, TypeError, KeyError):
            raise FireError(
                "Bad value of {}={} but must be: {}".format(field_name, value, error_msg)
            )

    def _unparse_value(self, value: Optional[Any], field_datatype) -> str:
        if value is None:
            return ''
        if issubclass(field_datatype, Enum):
            return value.name

        return self._output_converters[field_datatype](value)

    def _parse_tuple(self, value: str) -> tuple:
        return tuple(value.split(self.TUPLE_SEPARATOR))

    def _unparse_tuple(self, value: tuple) -> str:
        return self.TUPLE_SEPARATOR.join(self._unparse_value(x, type(x)) for x in value)

    def _parse_daylight_saving_moment_mode1(self, value: str) -> DaylightSavingMomentMode1:
        args = [int(x) for x in self._parse_tuple(value)]
        if len(args) != 4:
            raise ValueError('Daylight saving moment value must contain 4 integers')
        return DaylightSavingMomentMode1(*args)

    def _parse_daylight_saving_moment_mode2(self, value: str) -> DaylightSavingMomentMode2:
        args = [int(x) for x in self._parse_tuple(value)]
        if len(args) != 7:
            raise ValueError('Daylight saving moment value must contain 7 integers')

        is_daylight = bool(args[5])
        buffer_size = args[6]
        res = DaylightSavingMomentMode2(None, is_daylight, buffer_size)
        for ind, attr in enumerate(('month', 'week_of_month', 'day_of_week', 'hour', 'minute')):
            setattr(res, attr, args[ind])

        return res

    def _unparse_daylight_saving_moment_mode2(self, value: DaylightSavingMomentMode2) -> str:
        res = [
            str(getattr(value, attr))
            for attr in ('month', 'week_of_month', 'day_of_week', 'hour', 'minute')
        ]
        res.extend((str(int(value.is_daylight)), str(value.buffer_size)))
        return self.TUPLE_SEPARATOR.join(res)


class ModelConverter(TypedFieldConverter):
    """Converter performs text input/output for a Model objects"""
    TUPLE_SEPARATOR = ','

    def __init__(self, formatter: BaseFormatter, model_cls: Type[Model], *args, **kwargs):
        field_types = {k: getattr(model_cls, k).field_datatype
                       for k in model_cls.fields_mapping().keys()}
        super().__init__(formatter, field_types, *args, **kwargs)
        self._model_cls = model_cls
        self._model_fields = {k: getattr(self._model_cls, k)
                              for k in self._model_cls.fields_mapping().keys()}

    def read_records(self) -> Generator[Model, None, None]:
        for item in self._formatter.get_reader():
            model_dict = self.to_record_dict(item)
            yield self._model_cls(**model_dict)

    def write_records(self, records: Iterable[Model]):
        writer = self._formatter.get_writer()
        for item in records:
            record = self.to_string_dict(item.dict)
            writer.write(record)

        writer.flush()

    def to_record_dict(self, record: Mapping[str, str]) -> Mapping[str, Any]:
        self._validate_field_names(self._model_fields.keys(), record)

        # Convert dict with text values to a model with typed values
        return {fname: self._parse_value(fname, fval, self._model_fields[fname].field_datatype)
                for fname, fval in record.items()}

    def to_string_dict(self, model_dict: Mapping[str, Any]) -> Mapping[str, str]:
        self._validate_field_names(self._model_fields.keys(), model_dict)

        # Convert a model to text values
        return {fname: self._unparse_value(fval, self._model_fields[fname].field_datatype)
                for fname, fval in model_dict.items()}

    def _validate_field_names(self, fields: Union[Set[str], KeysView], item: Mapping[str, Any]):
        # Check if field names are all exist in the model
        extra_fields = item.keys() - fields
        if extra_fields:
            raise FireError("Unknown fields of {} found in the input data: {}".format(
                self._model_cls.__name__, list(sorted(extra_fields))
            ))


def parse_array_index(opt_indexes: Optional[Union[int, str]]) -> Union[int, slice]:
    """
    Parse index/range cli parameter and return appropriate int or slice

        >>> assert parse_array_index(None) == slice(None, None, None)
        >>> assert parse_array_index(1) == int(1)
        >>> assert parse_array_index('1-2') == slice(1, 2, None)

    Args:
        opt_indexes(Union[int, str], optional): index or range

    Returns:
        Union[int, slice]: int or slice suitable for sequences indexing
    """
    if opt_indexes is None:
        return slice(None, None)
    if isinstance(opt_indexes, str):
        if not re.match(r'^\d-\d$', opt_indexes):
            raise FireError("Select range must contain numbers divided by dash, for example 0-3")

        pieces = opt_indexes.split('-')
        start = int(pieces.pop(0)) if pieces else None
        stop = int(pieces.pop(0) or 1000) + 1 if pieces else None
        return slice(start, stop)
    if isinstance(opt_indexes, int):
        if opt_indexes < 0:
            raise FireError("Select index must be a positive number")

        return opt_indexes

    raise FireError("Numbers must be list or int")


class Query:
    """This command object helps to make read/write queries to a
    particular device data table.

    Some of usage examples:

        Select all records from the User table:
            $ ... table User

        Select records from the User table with card=123456 AND group=4:
            $ ... table User where --card=123456 --group=4

        Get table records count:
            $ ... table User count

        Upsert records to the User table from stdin:
            $ cat records.csv | ... table User upsert

        Delete records, which come from stdin, from the User table:
            $ cat records.csv | ... table User delete

        Delete records from the User table with card=123456 AND group=4:
            $ ... table User where --card=123456 --group=4 delete_all
    """
    def __init__(self, qs: QuerySet, io_converter: ModelConverter):
        self._qs = qs
        self._io_converter = io_converter

    def __call__(self):
        if self._qs is not None:
            self._io_converter.write_records(self._qs)

    def where(self, **filters) -> 'Query':
        """Add filtering by fields to a query.

        Filtering conditions are set by flags. Several conditions will
        be AND'ed.

        For example, select Users records with card=123456 AND group=4:
            $ ... table User where --card=123456 --group=4

        Args:
            filters: flags are fields to do filtering by. Such
                filters are concatenated by AND. For example,
                `... where --field1=value1 --field2=value2 ...`
        """
        typed_filters = self._io_converter.to_record_dict(filters)
        self._qs = self._qs.where(**typed_filters)

        return self

    def unread(self) -> 'Query':
        """Add condition to print unread records only.

         Some tables on device has a pointer which is set to the last
        record on each query. If no records have been inserted to
        a table since last read, the "unread" query will return nothing

        For example, select only unread Users records with card=123456
             $ ... table User where --card=123456 unread
        """
        self._qs = self._qs.unread()
        return self

    def upsert(self):
        """Upsert (update or insert) operation.

        If given record already exists in a table, then it will be
        updated. Otherwise it will be inserted. Consumes input data
        from stdin/file.

        For example, upsert records to the User table from stdin:
            $ cat records.csv | ... table User upsert
        """

        self._qs.upsert(self._io_converter.read_records())
        self._qs = None

    def delete(self):
        """Delete given records from a table.

        If given record does not exist in a table, then it is skipped.
        Consumes input data from stdin/file.

        For example, delete records, which come from stdin, from the User table:
            $ cat records.csv | ... table User delete
        """
        self._qs.delete(self._io_converter.read_records())
        self._qs = None

    def delete_all(self):
        """Delete records satisfied to a query.

        For example, Delete records from the User table with card=123456 AND group=4:
            $ ... table User where --card=123456 --group=4 delete_all

        Or delete all records from the User table:
            $ ... table User delete_all
        """
        self._qs.delete_all()
        self._qs = None

    def count(self):
        """Return records count in a table. Executes quickly since
        it is implemented by a separate device request.

        For example, get records count in the User table:
            $ ... table User count
        """
        res = self._qs.count()
        self._qs = None
        return res


class Doors:
    """This group gives access to inputs and outputs related
    to a given door or doors
    """
    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, list]):
        """Select doors to operate

        Args:
            indexes: Doors to select. You can select a single door by
                passing an index `select 1`. Or select a range by
                passing a list as `select 0-2` (doors 0, 1 and 2
                will be selected). Indexes are started from 0.
        """
        self._items = self._items[parse_array_index(indexes)]
        return self

    @property
    def relays(self):
        return Relays(self._items.relays)

    @property
    def readers(self):
        if isinstance(self._items, Door):
            return Readers(self._items.reader)
        return Readers(self._items.readers)

    @property
    def aux_inputs(self):
        if isinstance(self._items, Door):
            return AuxInputs(self._items.aux_input)
        return AuxInputs(self._items.aux_inputs)

    @property
    def parameters(self):
        """Parameters related to a current door. Valid only if a
        single door was requested

        Args:
            names: Comma-separated list of parameter names to request
                from a device. If omitted, then all parameters will be
                requested. For example, --names=param1,param2,param3
        """
        if isinstance(self._items, Door):
            return Parameters(self._items.parameters)
        return Parameters(doors_params_error)

    @property
    def events(self):
        return Events(self._items.events)


class Relays:
    """This group provides actions to do with a given relay or
    relays
    """
    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, list]):
        """
        Select relays to operate

        Args:
            indexes: Relays to select. You can select a single relay by
                passing an index `select 1`. Or select a range by
                passing a list as `select 0-2` (relays 0, 1 and 2
                will be selected). Indexes are started from 0.
        """
        self._items = self._items[parse_array_index(indexes)]
        return self

    def switch_on(self, *, timeout: int = 5):
        """Switch on a relay for given time.

        Args:
            timeout: Timeout in seconds in which a relay(s) will be
            switched on. Default is 5 seconds
        """
        self._items.switch_on(timeout)


class Readers:
    """This group represents a given reader or readers"""
    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, list]):
        """Select doors to operate

        Args:
            indexes: Readers to select. You can select a single reader
                by passing an index `select 1`. Or select a range by
                passing a list as `select 0-2` (readers 0, 1 and 2
                will be selected). Indexes are started from 0.
        """
        self._items = self._items[parse_array_index(indexes)]
        return self

    @property
    def events(self):
        return Events(self._items.events)


class AuxInputs:
    """This group represents a given aux input or inputs"""
    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, list]):
        """Select doors to operate

        Args:
            indexes: Aux input to select. You can select a single
                aux input by passing an index `select 1`. Or select
                a range by passing a list as `select 0-2` (aux inputs
                0, 1 and 2 will be selected). Indexes are started
                from 0.
        """
        self._items = self._items[parse_array_index(indexes)]
        return self

    @property
    def events(self):
        return Events(self._items.events)


class Events:
    """This group is intended for working with event log"""
    def __init__(self, event_log):
        self._event_log = event_log
        self._event_field_types = {
            'time': datetime,
            'pin': str,
            'card': str,
            'door': int,
            'event_type': int,
            'entry_exit': PassageDirection,
            'verify_mode': VerifyMode
        }
        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, self._event_field_types.keys()
        )
        # Use ad-hoc formatter because ascii table formatter
        # can't print data iteratively as it arrives, and whole contents
        # prints only when poll function exits by timeout
        if opt_io_format == 'ascii_table':
            formatter = EventsPollFormatter(data_in, data_out, self._event_field_types.keys())

        self._io_converter = TypedFieldConverter(formatter, self._event_field_types)

    def __call__(self):
        self._io_converter.write_records(
            {s: getattr(ev, s) for s in self._event_field_types.keys()} for ev in self._event_log
        )

    def poll(self, timeout: int = 60, first_only: bool = False):
        """Wait for an event to be appeared on a device and prints
        them if any. If no events has been appeared during timeout, then
        exit by timeout. Filters that has been set are also matter.


        Args:
            timeout: Time in seconds the command waits events
                to appear and then finishes if no events has been
                appeared. Default is 60 seconds
            first_only: If this flag is set then the command will exit
                after the first event has came
        """
        def _poll_events():
            events = self._event_log.poll(timeout)
            while events:
                for event in events:
                    yield {s: getattr(event, s) for s in self._event_field_types.keys()}

                if first_only:
                    return

                events = self._event_log.poll(timeout)

            sys.stderr.write('INFO: Finished by timeout\n')

        self._io_converter.write_records(_poll_events())

    def only(self, **filters):
        """Add filtering by field value to an event log

        For example, select events with card=123456 AND event_type=221:
            $ ... events only --card=123456 --event_type=221

        Args:
            filters: flags are fields to do filtering by. Such
                filters are concatenated by AND. For example,
                `... only --field1=value1 --field2=value2 ...`
        """
        typed_filters = self._io_converter.to_record_dict(filters)
        self._event_log = self._event_log.only(**typed_filters)

        return self


class Parameters:
    """This group helps to get and set device and door parameters

    Some of usage examples:

        List all door parameter names:
            $ ... doors --numbers=1 parameters list

        List all device parameter names:
            $ ... parameters list

        Get all device parameters with values:
            $ ... parameters

        Get particular device parameters with values (could be faster than requesting all ones):
            $ ... parameters --names=datetime,ip_address,serial_number

        Set device parameters:
            $ ... parameters set --datetime="2021-05-08 00:04:00" --ip_address="192.168.128.1"

    Args:
        names: Comma-separated list of parameter names to request
            from a device. If omitted, then all parameters will be
            requested. For example, --names=param1,param2,param3

    """
    def __init__(self, item):
        self._item = item
        self._item_cls = item.__class__
        # Exclude write-only parameters
        self._readable_params = {attr for attr in dir(self._item_cls)
                                 if (isinstance(getattr(self._item_cls, attr), property)
                                 and getattr(self._item_cls, attr).fget is not None)}
        self._readonly_params = {attr for attr in self._readable_params
                                 if getattr(self._item_cls, attr).fset is None}
        # Extract types from getters annotations. Skip if no getter
        # Assume str if no return annotation has set
        props = {attr: getattr(self._item_cls, attr) for attr in self._readable_params
                 if getattr(self._item_cls, attr).fget is not None}
        self._prop_types = {k: getattr(v.fget, '__annotations__', {}).get('return', str)
                            for k, v in props.items()}

    def __call__(self, *, names: list = None):
        if self._item is doors_params_error:
            raise FireError('Parameters may be used only for single door')

        if names is None:
            names = self._readable_params
        elif isinstance(names, str):
            names = (names, )
        elif not isinstance(names, (list, tuple)):
            # Workaround of "Could not consume arg" message appearing
            # instead of exception message problem
            sys.stderr.write("ERROR: Names must be a name or list of parameters")
            raise FireError("Names must be a name or list of parameters")

        names = set(names)

        extra_names = names - set(self._readable_params)
        if extra_names:
            # Workaround of "Could not consume arg" message appearing
            # instead of exception message problem
            sys.stderr.write('ERROR: Unknown parameters were given: {}\n'.format(extra_names))
            raise FireError('Unknown parameters were given: {}'.format(extra_names))

        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, names
        )
        converter = TypedFieldConverter(formatter, self._prop_types)
        converter.write_records(
            [{name: getattr(self._item, name) for name in sorted(names)}]
        )

    def list(self):
        """List of all valid parameter names"""
        if self._item is doors_params_error:
            raise FireError('Parameters may be used only for single door')

        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, ['parameter_name']
        )
        converter = TextConverter(formatter)
        converter.write_records({'parameter_name': x} for x in sorted(self._readable_params))

    def set(self, **parameters):
        """Set given parameters

        Args:
            parameters: Flags are parameters with values to be set.
                For example, `... parameters set --param1=value1 --param2=value2 ...`
        """
        if self._item is doors_params_error:
            raise FireError('Parameters may be used only for single door')

        readonly_params = parameters.keys() & self._readonly_params
        if readonly_params:
            raise FireError('The following parameters are read-only: {}'.format(readonly_params))

        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, parameters.keys()
        )
        converter = TypedFieldConverter(formatter, self._prop_types)
        if parameters:
            self._set_from_args(parameters, converter)
        else:
            self._set_from_input(converter)

    def _set_from_input(self, converter):
        for record in converter.read_records():
            for k, v in record.items():
                setattr(self._item, k, v)

    def _set_from_args(self, args: dict, converter):
        extra_names = args.keys() - set(self._readable_params)
        if extra_names:
            raise FireError('Unknown parameters were given: {}'.format(extra_names))

        typed_items = converter.to_record_dict(args)
        for name, val in typed_items.items():
            setattr(self._item, name, val)


class ZKCommand:
    def __init__(self, zk: ZKAccess):
        self._zk = zk

    def table(self, name: str) -> Query:
        """
        Make a query to a device table with given name
        
        Args:
            name: table name. Possible values are:
                'User', 'UserAuthorize', 'Holiday', 'Timezone',
                'Transaction', 'FirstCard', 'MultiCard', 'InOutFun',
                'TemplateV10'
        """
        if name not in models_registry:
            raise FireError("Unknown table '{}', possible values are: {}".format(
                name, list(sorted(models_registry.keys()))
            ))
        qs = self._zk.table(name)
        table_cls = qs._table_cls
        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, table_cls.fields_mapping().keys()
        )
        return Query(qs, ModelConverter(formatter, table_cls))

    def read_raw(self, name: str, *, buffer_size=32768):
        """Return raw data from a given table.

        ZKAccess device keeps table values as strings, many of these
        fields are encoded (some date fields, for instance). This
        command returns data as it stores on a device, without
        applying any type convertions or decoding, like `table`
        command does.

        This command works on low level. So, it accepts buffer size
        for storing a result. If you are observed that results
        are cut, its makes sense to increase buffer size.

        Args:
            name: table name. Possible values are:
                'User', 'UserAuthorize', 'Holiday', 'Timezone',
                'Transaction', 'FirstCard', 'MultiCard', 'InOutFun',
                'TemplateV10'
            buffer_size: buffer size in bytes to store a result.
                Default is 32Kb
        """
        if name not in models_registry:
            raise FireError("Unknown table '{}', possible values are: {}".format(
                name, list(sorted(models_registry.keys()))
            ))
        table_cls = models_registry[name]
        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, table_cls.fields_mapping().values()
        )
        converter = TextConverter(formatter)
        converter.write_records(
            self._zk.sdk.get_device_data(table_cls.table_name, [], {}, buffer_size, False)
        )

    def write_raw(self, name: str):
        """Write raw data to a given table.

        ZKAccess device keeps table values as strings, many of these
        fields are encoded (some date fields, for instance). This
        command expects input data as it stores on a device, without
        applying any type convertions or decoding (like `table`
        command does).

        Args:
            name: table name. Possible values are:
                'User', 'UserAuthorize', 'Holiday', 'Timezone',
                'Transaction', 'FirstCard', 'MultiCard', 'InOutFun',
                'TemplateV10'
        """
        if name not in models_registry:
            raise FireError("Unknown table '{}', possible values are: {}".format(
                name, list(sorted(models_registry.keys()))
            ))
        table_cls = models_registry[name]
        formatter = BaseFormatter.get_formatter(opt_io_format)(
            data_in, data_out, table_cls.fields_mapping().values()
        )
        converter = TextConverter(formatter)

        gen = self._zk.sdk.set_device_data(table_cls.table_name)
        gen.send(None)
        for record in converter.read_records():
            gen.send(record)

        try:
            gen.send(None)
        except StopIteration:
            pass

    @property
    def doors(self) -> Doors:
        """Select doors to operate. This command gives access to
        operate with relays, reader and aux input related to selected
        doors. By default, all doors are selected. Doors count depends
        on a device model.
        """
        return Doors(self._zk.doors)

    @property
    def relays(self):
        """Select relays to operate. By default, all relays are
        seleted. Relays count depends on a device model.
        """
        return Relays(self._zk.relays)

    @property
    def readers(self):
        """Select readers to operate. By default, all readers are
        seleted. Readers count depends on a device model.
        """
        return Readers(self._zk.readers)

    @property
    def aux_inputs(self):
        """Aux inputs to operate. By default, all aux inputs are
        seleted. Aux inputs count depends on a device model.
        """
        return AuxInputs(self._zk.aux_inputs)

    @property
    def events(self):
        """Events on a device."""
        return Events(self._zk.events)

    @property
    def parameters(self):
        """Device parameters. They does not include door parameters
        that are available via `doors` command.
        """
        return Parameters(self._zk.parameters)

    def restart(self):
        """Restart a device."""
        self._zk.restart()


class CLI:
    """PyZKAccess command-line interface

    Typical CLI usage:
        Commands for a connected device:
            $ pyzkaccess connect <ip> <subcommand|group> [parameters] [<subcommand> [parameters] ...]

        Commands not related to a particular device:
            $ pyzkaccess <command> [parameters]

    Every command, group and subcommand has its own help contents, just
    type them and append `--help` at the end.

    For example, getting help for `connect` command:
        $ pyzkaccess connect --help

    Or for `where` subcommand of `table` subcommand:
        $ pyzkaccess connect 192.168.1.201 table User where --help

    Args:
        format: format for input/output. Possible values are: ascii_table,
            csv. Default is ascii_table.
        file: read and write to/from this file instead of stdin/stdout
        dllpath: path to PULL SDK dll file. Default is just
            "plcommpro.dll"
    """
    def __init__(self):
        self.__call__()

    def __call__(
            self, *, format: str = 'ascii_table', file: str = None, dllpath: str = 'plcommpro.dll'
    ):
        if format not in io_formats:
            # Workaround of "Could not consume arg" message appearing
            # instead of exception message problem
            sys.stderr.write("ERROR: Unknown format '{}', available are: {}\n".format(
                format, list(sorted(io_formats.keys()))
            ))
            raise FireError("Unknown format '{}', available are: {}".format(
                format, list(sorted(io_formats.keys()))
            ))

        if isinstance(pyzkaccess.ctypes_.WinDLL, Mock):
            sys.stderr.write("WARN: PyZKAccess doesn't work on non-Windows system. "
                             "Actually you can see CLI help contents only\n")

        global opt_io_format
        opt_io_format = format

        self._file = None
        if file:
            d = os.path.dirname(file)
            if not os.path.isdir(d):
                # Workaround of "Could not consume arg" message appearing
                # instead of exception message problem
                sys.stderr.write("ERROR: Directory '{}' does not exist\n".format(d))
                raise FireError("Directory {} does not exist".format(d))

            self._file = open(file, 'r+')
            self._file.seek(0)

            global data_in
            global data_out
            data_out = data_in = self._file

        self._dllpath = dllpath

        return self

    def connect(self, ip: str, *, model: str = 'ZK400') -> ZKCommand:
        """
        Connect to a device with given ip.

        Args:
            ip (str): IP address of a device
            model (DeviceModels): device model. Possible values are:
            ZK100, ZK200, ZK400
        """
        model = device_models.get(model)
        if model is None:
            raise FireError(
                "Unknown device model '{}', possible values are: ZK100, ZK200, ZK400".format(model)
            )

        if not ip:
            raise FireError('IP argument is required')

        connstr = 'protocol=TCP,ipaddress={},port=4370,timeout=4000,passwd='.format(ip)

        zkcmd = ZKCommand(ZKAccess(connstr, device_model=model, dllpath=self._dllpath))

        return zkcmd

    @staticmethod
    def search_devices(*, broadcast_address: str = '255.255.255.255'):
        """
        Search devices online by scanning an IP local network with given
        broadcast address

        Args:
            broadcast_address: Address for broadcast IP packets. Default: 255.255.255.255
        """
        headers = ['mac', 'ip', 'serial_number', 'model', 'version']
        formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out, headers)
        converter = TextConverter(formatter)

        def _search_devices():
            devices = ZKAccess.search_devices(broadcast_address)
            for device in devices:
                values = [
                    device.mac, device.ip, device.serial_number, device.model.name, device.version
                ]
                yield dict(zip(headers, values))

        converter.write_records(_search_devices())


def main():
    cli = CLI()
    fire.Fire(cli)

    if cli._file is not None:
        cli._file.close()


if __name__ == '__main__':
    main()
