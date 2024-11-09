import abc
import csv
import io
import ipaddress
import os
import re
import sys
import traceback
from datetime import date, datetime, time
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Generic,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    Optional,
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import fire
import prettytable
import wrapt
from fire.core import FireError

from pyzkaccess import (
    ZK100,
    ZK200,
    ZK400,
    AuxInput,
    Door,
    Reader,
    Relay,
    UnsupportedPlatformError,
    ZKAccess,
    ZKModel,
    ZKSDKError,
)
from pyzkaccess._setup import setup
from pyzkaccess.device_data.model import Model, models_registry
from pyzkaccess.device_data.queryset import QuerySet
from pyzkaccess.enums import ChangeIPProtocol, PassageDirection, VerifyMode
from pyzkaccess.param import DaylightSavingMomentMode1, DaylightSavingMomentMode2

DEVICE_MODELS: Final[Dict[str, Type[ZKModel]]] = {"ZK100": ZK100, "ZK200": ZK200, "ZK400": ZK400}

OPT_IO_FORMAT: str = "csv"
DATA_IN = sys.stdin
DATA_OUT = sys.stdout


DOORS_PARAMS_ERROR: Final[object] = object()


class BaseFormatter(metaclass=abc.ABCMeta):
    """Base class for formatters

    Formatters are used to read and write the structured data in
    a particular format.
    """

    class WriterInterface(metaclass=abc.ABCMeta):
        _writer: Optional[Any]

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
    def get_formatter(io_format: str) -> "Type[BaseFormatter]":
        if io_format not in IO_FORMATS:
            raise FireError(f"{sorted(IO_FORMATS.keys())} format(s) are only supported")
        return IO_FORMATS[io_format]

    def validate_headers(self, input_headers: Union[set, KeysView]) -> None:
        headers = set(self._headers)
        extra = input_headers - headers
        if extra:
            raise FireError(f"Unknown fields in input: {extra}")

        missed = headers - input_headers
        if missed:
            raise FireError(f"Missed fields in input: {extra}")

    @abc.abstractmethod
    def get_reader(self) -> Iterable[Mapping[str, str]]:
        pass

    @abc.abstractmethod
    def get_writer(self) -> WriterInterface:
        pass


class CSVFormatter(BaseFormatter):
    """Formatter for comma-separated values format"""

    class CSVWriter(BaseFormatter.WriterInterface):
        _writer: Optional[csv.DictWriter]

        def write(self, record: Mapping[str, str]) -> None:
            row = {k: record.get(k) for k in self._headers}

            if self._writer is None:
                self._writer = csv.DictWriter(self._ostream, self._headers)
                self._writer.writeheader()

            self._writer.writerow(row)

        def flush(self) -> None:
            if self._writer is None:
                self._writer = csv.DictWriter(self._ostream, self._headers)
                self._writer.writeheader()

            self._ostream.flush()

    def get_reader(self) -> Iterator[Mapping[str, str]]:
        def _reader() -> Iterator[Dict[str, str]]:
            checked = False
            for item in csv.DictReader(self._istream):
                if checked is False:
                    self.validate_headers(item.keys())
                    checked = True

                item = {k: item[k] for k in self._headers}
                yield item

        return _reader()

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return CSVFormatter.CSVWriter(self._ostream, self._headers)


class ASCIITableFormatter(BaseFormatter):
    """Formatter for ASCII table format"""

    class ASCIITableWriter(BaseFormatter.WriterInterface):
        _writer: Optional[prettytable.PrettyTable]

        def write(self, record: Mapping[str, str]) -> None:
            if self._writer is None:
                self._writer = prettytable.PrettyTable(field_names=self._headers, align="l")

            row = [record.get(k) for k in self._headers]
            self._writer.add_row(row)

        def flush(self) -> None:
            if self._writer is None:
                self._writer = prettytable.PrettyTable(field_names=self._headers, align="l")

            self._ostream.write(self._writer.get_string())
            self._ostream.write("\n")
            self._ostream.flush()

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return ASCIITableFormatter.ASCIITableWriter(self._ostream, self._headers)

    def get_reader(self) -> Iterable[Mapping[str, str]]:
        raise FireError("You should to specify input data format, e.g. `pyzkaccess --format=csv ...`")


class EventsPollFormatter(CSVFormatter):
    """Special formatter that writes the data in live mode as it appears
    in the input stream instead of writing all data at once.
    """

    class ASCIITableWriter(BaseFormatter.WriterInterface):
        _writer: Optional[str]
        FIELD_FORMAT = "{:<15}{:<5}{:<15}{:<15}{:<5}{:<25}{:<15}"

        def write(self, record: Mapping[str, str]) -> None:
            if self._writer is None:
                self._writer = self.FIELD_FORMAT
                self._ostream.write(self._writer.format(*self._headers))
                self._ostream.write("\n")

            row = [str(record.get(k) or "") for k in self._headers]
            self._ostream.write(self._writer.format(*row))
            self._ostream.write("\n")
            self._ostream.flush()

        def flush(self) -> None:
            if self._writer is None:
                self._writer = self.FIELD_FORMAT
                self._ostream.write(self._writer.format(*self._headers))
                self._ostream.write("\n")

            self._ostream.flush()

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return EventsPollFormatter.ASCIITableWriter(self._ostream, self._headers)


IO_FORMATS: Final[Dict[str, Type[BaseFormatter]]] = {"csv": CSVFormatter, "ascii_table": ASCIITableFormatter}


class BaseConverter(metaclass=abc.ABCMeta):
    """Converter receives the raw string data and parses and converts it
    to the objects of a particular type. It also converts the objects to
    the string data suitable for output
    """

    def __init__(self, formatter: BaseFormatter, *args: Any, **kwargs: Any) -> None:
        self._formatter = formatter
        self._args = args
        self._kwargs = kwargs

    @abc.abstractmethod
    def read_records(self) -> Iterator[Mapping[str, Any]]:
        pass

    @abc.abstractmethod
    def write_records(self, records: Iterable[Mapping[str, Any]]) -> None:
        pass


class TextConverter(BaseConverter):
    """Converter, that simply prints and reads text field values without
    any transformations
    """

    def read_records(self) -> Iterator[Mapping[str, Any]]:
        for item in self._formatter.get_reader():
            yield item

    def write_records(self, records: Iterable[Mapping[str, Any]]) -> None:
        writer = self._formatter.get_writer()
        for item in records:
            writer.write(item)

        writer.flush()


class TypedFieldConverter(BaseConverter):
    """Converter, that initially accepts the fields types mapping and converts
    the text field values to Python objects. Also it converts Python objects
    to the string representation.
    """

    TUPLE_SEPARATOR = ","

    def __init__(self, formatter: BaseFormatter, field_types: Mapping[str, Type], *args: Any, **kwargs: Any) -> None:
        super().__init__(formatter, *args, **kwargs)
        self._field_types = field_types

        # The following converters parses string value respresentation from
        # stdin and converts to a field value
        # {type: (cast_function, error message)
        self._input_converters: Mapping[Type, Tuple[Callable[[str], Any], str]] = {
            str: (str, "string"),
            bool: (
                lambda x: {"True": True, "False": False}[x.capitalize()] if isinstance(x, str) else bool(x),
                "boolean, possible values: True, true, 1, False, false, 0",
            ),
            int: (int, "integer"),
            tuple: (self._parse_tuple, "comma separated values"),
            date: (lambda x: datetime.strptime(x, "%Y-%m-%d").date(), 'date string, e.g. "2020-02-01"'),
            time: (lambda x: datetime.strptime(x, "%H:%M:%S").time(), 'time string, e.g. "07:40:00"'),
            datetime: (
                lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
                'datetime string, e.g. "2020-02-01 07:40:00"',
            ),
            DaylightSavingMomentMode1: (
                lambda x: DaylightSavingMomentMode1.strptime(x, "%m-%d %H:%M"),
                'datetime moment, e.g. "02-01 07:40"',
            ),
            DaylightSavingMomentMode2: (
                self._parse_daylight_saving_moment_mode2,
                "7 comma-separated values, "
                "[month, week_of_month, day_of_week, hour, minute, is_daylight, buffer_size], "
                'e.g "2,1,1,7,40,1,4096"',
            ),
        }

        # The following functions converts field values to their string
        # representation suitable for stdout output
        self._output_converters: Mapping[Type, Callable[[Any], Any]] = {
            str: str,
            bool: str,
            int: str,
            tuple: self._coalesce_tuple,
            date: lambda x: x.strftime("%Y-%m-%d"),
            time: lambda x: x.strftime("%H:%M:%S"),
            datetime: lambda x: x.strftime("%Y-%m-%d %H:%M:%S"),
            DaylightSavingMomentMode1: lambda x: x.strftime("%m-%d %H:%M"),
            DaylightSavingMomentMode2: self._coalesce_daylight_saving_moment_mode2,
        }

    def read_records(self) -> Iterator[Mapping[str, Any]]:
        for item in self._formatter.get_reader():
            # Convert a text field value to a typed value
            yield self.to_record_dict(item)

    def write_records(self, records: Iterable[Mapping[str, Any]]) -> None:
        writer = self._formatter.get_writer()
        for item in records:
            # Convert a typed field value to a string value
            record = self.to_string_dict(item)
            writer.write(record)

        writer.flush()

    def to_record_dict(self, data: Mapping[str, str]) -> Mapping[str, Any]:
        return {
            fname: self._parse_value(fname, fval, self._field_types.get(fname, str)) for fname, fval in data.items()
        }

    def to_string_dict(self, record: Mapping[str, Any]) -> Mapping[str, str]:
        return {fname: self._coalesce_value(fval, self._field_types.get(fname, str)) for fname, fval in record.items()}

    def _parse_value(self, field_name: str, value: str, field_datatype: Type) -> Optional[Any]:
        if value == "":
            return None

        error_msg = ""
        try:
            if issubclass(field_datatype, Enum):
                error_msg = f"one of values: {','.join(x for x in dir(field_datatype) if not x.startswith('_'))}"
                return field_datatype[value]

            cast_fn, error_msg = self._input_converters[field_datatype]
            return cast_fn(value)
        except (ValueError, TypeError, KeyError):
            raise FireError(f"Bad value of {field_name}={value}, must be: {error_msg}")

    def _coalesce_value(self, value: Optional[Any], field_datatype: Type) -> str:
        if value is None:
            return ""
        if issubclass(field_datatype, Enum):
            return value.name

        return self._output_converters[field_datatype](value)

    def _parse_tuple(self, value: Union[str, tuple]) -> tuple:
        if isinstance(value, tuple):
            return value
        return tuple(value.split(self.TUPLE_SEPARATOR))

    def _coalesce_tuple(self, value: tuple) -> str:
        return self.TUPLE_SEPARATOR.join(self._coalesce_value(x, type(x)) for x in value)

    def _parse_daylight_saving_moment_mode1(self, value: str) -> DaylightSavingMomentMode1:
        args = [int(x) for x in self._parse_tuple(value)]
        if len(args) != 4:
            raise ValueError("Daylight saving moment value must contain 4 integers")
        return DaylightSavingMomentMode1(*args)

    def _parse_daylight_saving_moment_mode2(self, value: str) -> DaylightSavingMomentMode2:
        args = [int(x) for x in self._parse_tuple(value)]
        if len(args) != 7:
            raise ValueError("Daylight saving moment value must contain 7 integers")

        is_daylight = bool(args[5])
        buffer_size = args[6]
        res = DaylightSavingMomentMode2(None, is_daylight, buffer_size)
        for ind, attr in enumerate(("month", "week_of_month", "day_of_week", "hour", "minute")):
            setattr(res, attr, args[ind])

        return res

    def _coalesce_daylight_saving_moment_mode2(self, value: DaylightSavingMomentMode2) -> str:
        res = [str(getattr(value, attr)) for attr in ("month", "week_of_month", "day_of_week", "hour", "minute")]
        res.extend((str(int(value.is_daylight)), str(value.buffer_size)))
        return self.TUPLE_SEPARATOR.join(res)


_ModelT = TypeVar("_ModelT", bound=Model)


class ModelConverter(TypedFieldConverter, Generic[_ModelT]):
    """Converter, that accepts the model class and converts the text
    field values to the model objects. Also it converts the model objects
    to the string representation.
    """

    TUPLE_SEPARATOR = ","

    def __init__(self, formatter: BaseFormatter, model_cls: Type[_ModelT], *args: Any, **kwargs: Any) -> None:
        field_types = {k: getattr(model_cls, k).field_datatype for k in model_cls.fields_mapping().keys()}
        super().__init__(formatter, field_types, *args, **kwargs)
        self._model_cls = model_cls
        self._model_fields = {k: getattr(self._model_cls, k) for k in self._model_cls.fields_mapping().keys()}

    def read_records(self) -> Iterator[_ModelT]:
        for item in self._formatter.get_reader():
            model_dict = self.to_record_dict(item)
            yield self._model_cls(**model_dict)

    def write_records(self, records: Iterable[_ModelT]) -> None:
        writer = self._formatter.get_writer()
        for item in records:
            record = self.to_string_dict(item.dict)
            writer.write(record)

        writer.flush()

    def to_record_dict(self, record: Mapping[str, str]) -> Mapping[str, Any]:
        self._validate_field_names(self._model_fields.keys(), record)

        # Convert dict with text values to a model with typed values
        return {
            fname: self._parse_value(fname, fval, self._model_fields[fname].field_datatype)
            for fname, fval in record.items()
        }

    def to_string_dict(self, model_dict: Mapping[str, Any]) -> Mapping[str, str]:
        self._validate_field_names(self._model_fields.keys(), model_dict)

        # Convert a model to text values
        return {
            fname: self._coalesce_value(fval, self._model_fields[fname].field_datatype)
            for fname, fval in model_dict.items()
        }

    def _validate_field_names(self, fields: Union[Set[str], KeysView], item: Mapping[str, Any]) -> None:
        # Check if field names are all exist in the model
        extra_fields = item.keys() - fields
        if extra_fields:
            raise FireError(
                f"Unknown fields of {self._model_cls.__name__} found in the input data: {list(sorted(extra_fields))}"
            )


def parse_array_index(opt_indexes: Optional[Union[int, str]]) -> Union[int, slice]:
    """
    Parse index/range expression to a slice or int

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
        if not re.match(r"^\d-\d$", opt_indexes):
            raise FireError("Range must contain numbers divided by dash, e.g. 0-3")

        pieces = opt_indexes.split("-")
        start = int(pieces.pop(0)) if pieces else None
        stop = int(pieces.pop(0) or 1000) + 1 if pieces else None
        return slice(start, stop)
    if isinstance(opt_indexes, int):
        if opt_indexes < 0:
            raise FireError("Selection index must be a positive number")

        return opt_indexes

    raise FireError("Selection must be an integer or range")


class Query:
    """Query to a data table (read and write operations)

    Usage examples:

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

    def __init__(self, qs: QuerySet, io_converter: ModelConverter) -> None:
        self._qs = qs
        self._io_converter = io_converter

    def __call__(self):
        if self._qs is not None:
            self._io_converter.write_records(self._qs)

    def where(self, **filters) -> "Query":
        """Add filter to a query. Fields to filter by are passed as flags.

        It's similar to SQL WHERE clause. Supports only the equality
        operation due to SDK limitations. Flags are AND'ed.
        Repeatable calls will also be AND'ed.

        Usage examples:

            Select Users with super rights AND who belongs to group="4":
                $ ... table User where --group=4 --super_authorize=1

            This is equal to:
                $ ... table User where --group=4 where --super_authorize=1

        Args:
            filters: Values to filter by, only equality is supported, e.g. --field=value
        """
        typed_filters = self._io_converter.to_record_dict(filters)
        self._qs = self._qs.where(**typed_filters)

        return self

    def unread(self) -> "Query":
        """Return only unread records.

        The ZK device stores a pointer to the last read record in each table.
        Once a table is read, the pointer is moved to the last record.
        We use this to track the unread records.

        Usage examples:

            Select only the Users with card=123456, that have not been read yet:
                $ ... table User where --card=123456 unread
        """
        self._qs = self._qs.unread()
        return self

    def upsert(self):
        """Upsert (update or insert) operation. Receives the data from stdin/file.

        If given record already exists in a table, then it will be
        updated, otherwise it will be inserted.

        Usage examples:

            Upsert the records coming from stdin in CSV format to the User table:
                $ cat records.csv | pyzkaccess --format=csv connect 1.2.3.4 table User upsert
        """

        self._qs.upsert(self._io_converter.read_records())
        self._qs = None

    def delete(self):
        """Delete given records from a table. Receives the data from stdin/file.

        If given record does not exist in a table, then it is skipped.

        Usage examples:

            Delete the records coming from stdin in CSV format from the User table:
                $ cat records.csv | pyzkaccess --format=csv connect 1.2.3.4 table User delete
        """
        self._qs.delete(self._io_converter.read_records())
        self._qs = None

    def delete_all(self):
        """Delete records satisfied to a query.

        Usage examples:

            Delete Users with super rights AND who belongs to group="4":
                $ ... table User where --group=4 --super_authorize=1 delete_all

            Delete all Users:
                $ ... table User delete_all
        """
        self._qs.delete_all()
        self._qs = None

    def count(self):
        """Return total count of records in the table.

        This command is fast, because it uses a separate SDK call
        (it doesn't enumerate all records counting them).

        Usage examples:

            Get records count in the User table:
                $ ... table User count
        """
        res = self._qs.count()
        self._qs = None
        return res


class Doors:
    """This group aggregates the inputs and outputs related to a door or doors"""

    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, str]):
        """Select doors to operate

        Args:
            indexes: Doors to select. Accepts index `select 2` or
                range `select 0-2`. Indexes are started from 0.
        """
        if isinstance(self._items, Door):
            raise FireError("A single door is already selected")

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
        """
        if isinstance(self._items, Door):
            return Parameters(self._items.parameters)
        return Parameters(DOORS_PARAMS_ERROR)

    @property
    def events(self):
        return Events(self._items.events)


class Relays:
    """This group aggregates an on board relay or relays"""

    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, str]):
        """
        Select relays to operate

        Args:
            indexes: Relays to select. Accepts index `select 2` or
                range `select 0-2`. Indexes are started from 0.
        """
        if isinstance(self._items, Relay):
            raise FireError("A single relay is already selected")

        self._items = self._items[parse_array_index(indexes)]
        return self

    def switch_on(self, *, timeout: int = 5):
        """Switch on a relay for given time.

        Args:
            timeout: Timeout in seconds a relay(s) will be
            switched on. Default is 5 seconds
        """
        self._items.switch_on(timeout)


class Readers:
    """This group aggregates a given reader or readers"""

    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, str]):
        """Select doors to operate

        Args:
            indexes: Readers to select. Accepts index `select 2` or
                range `select 0-2`. Indexes are started from 0.
        """
        if isinstance(self._items, Reader):
            raise FireError("A single reader is already selected")

        self._items = self._items[parse_array_index(indexes)]
        return self

    @property
    def events(self):
        return Events(self._items.events)


class AuxInputs:
    """This group aggregates a given auxiliary input or inputs"""

    def __init__(self, items):
        self._items = items

    def select(self, indexes: Union[int, str]):
        """Select doors to operate

        Args:
            indexes: Aux input to select. Accepts index `select 2` or
                range `select 0-2`. Indexes are started from 0.
        """
        if isinstance(self._items, AuxInput):
            raise FireError("A single aux input is already selected")

        self._items = self._items[parse_array_index(indexes)]
        return self

    @property
    def events(self):
        return Events(self._items.events)


class Events:
    """This group is for working with the event log"""

    def __init__(self, event_log) -> None:
        self._event_log = event_log
        self._event_field_types: Mapping[str, Type] = {
            "time": datetime,
            "pin": str,
            "card": str,
            "door": int,
            "event_type": int,
            "entry_exit": PassageDirection,
            "verify_mode": VerifyMode,
        }
        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, self._event_field_types.keys())
        # Use ad-hoc formatter because ascii table formatter
        # can't print data iteratively as it arrives, and whole contents
        # prints only when poll function exits by timeout
        if OPT_IO_FORMAT == "ascii_table":
            formatter = EventsPollFormatter(DATA_IN, DATA_OUT, self._event_field_types.keys())

        self._io_converter = TypedFieldConverter(formatter, self._event_field_types)

    def __call__(self):
        self._event_log.refresh()
        self._io_converter.write_records(
            {s: getattr(ev, s) for s in self._event_field_types.keys()} for ev in self._event_log
        )

    def poll(self, timeout: int = 60, first_only: bool = False):
        """Print the events in live mode.

        Usage examples:

            Poll events for 60 seconds:
                $ ... events poll

            Poll events with filters applied:
                $ ... events poll --card=123456 --event_type=221

        Args:
            timeout: Exit if no event has been appeared during this time.
                Default is 60 seconds.
            first_only: If this flag is set then the command prints only
                the first event and exits.
        """

        def _poll_events() -> Iterator[Mapping[str, Any]]:
            events = self._event_log.poll(timeout)
            while events:
                for event in events:
                    yield {s: getattr(event, s) for s in self._event_field_types.keys()}

                if first_only:
                    return

                events = self._event_log.poll(timeout)

            sys.stderr.write("INFO: Finished by timeout\n")

        self._io_converter.write_records(_poll_events())

    def where_or(self, **filters):
        """Apply filters to the events log. Fields to filter by are passed as flags.
        The repeated calls are concatenated by OR.

        Usage examples:

            Get events with card=123456 AND event_type=221:
                $ ... events where_or --card=123456 --event_type=221

        Args:
            filters: flags are fields to do filtering by. Such
                filters are concatenated by AND. For example,
                `... where_or --field1=value1 --field2=value2 ...`
        """
        typed_filters = self._io_converter.to_record_dict(filters)
        self._event_log = self._event_log.where_or(**typed_filters)

        return self

    def only(self, **filters):
        """Alias for `where_or` method"""
        return self.where_or(**filters)


class Parameters:
    """This group helps to get and set device and door parameters

    Usage examples:

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
        self._readable_params = {
            attr
            for attr in dir(self._item_cls)
            if (isinstance(getattr(self._item_cls, attr), property) and getattr(self._item_cls, attr).fget is not None)
        }
        self._readonly_params = {attr for attr in self._readable_params if getattr(self._item_cls, attr).fset is None}
        # Extract types from getters annotations. Skip if no getter
        # Assume str if no return annotation has set
        props = {
            attr: getattr(self._item_cls, attr)
            for attr in self._readable_params
            if getattr(self._item_cls, attr).fget is not None
        }
        self._prop_types = {k: getattr(v.fget, "__annotations__", {}).get("return", str) for k, v in props.items()}

    def __call__(self, *, names: list = None):
        if self._item is DOORS_PARAMS_ERROR:
            raise FireError("Parameters may be used only for single door")

        if names is None:
            names = self._readable_params
        elif isinstance(names, str):
            names = (names,)
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
            sys.stderr.write(f"ERROR: Unknown parameters were given: {extra_names}\n")
            raise FireError(f"Unknown parameters were given: {extra_names}")

        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, names)
        converter = TypedFieldConverter(formatter, self._prop_types)
        converter.write_records([{name: getattr(self._item, name) for name in sorted(names)}])

    def list(self):
        """List of available parameter names"""
        if self._item is DOORS_PARAMS_ERROR:
            raise FireError("Parameters may be used only for single door")

        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, ["parameter_name"])
        converter = TextConverter(formatter)
        converter.write_records({"parameter_name": x} for x in sorted(self._readable_params))

    def set(self, **parameters):
        """Set parameters values

        Args:
            parameters: Parameters and values to set.
                Example -- `... parameters set --param1=value1 --param2=value2`
        """
        if self._item is DOORS_PARAMS_ERROR:
            raise FireError("Parameters may be used only for single door")

        readonly_params = parameters.keys() & self._readonly_params
        if readonly_params:
            raise FireError(f"The following parameters are read-only: {readonly_params}")

        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, parameters.keys())
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
            raise FireError(f"Unknown parameters were given: {extra_names}")

        typed_items = converter.to_record_dict(args)
        for name, val in typed_items.items():
            setattr(self._item, name, val)


class ZKCommand:
    def __init__(self, zk: ZKAccess):
        self._zk = zk

    def table(self, name: str) -> Query:
        """
        Data table query builder (read and write operations)

        Args:
            name: table name. Possible values are:
                'User', 'UserAuthorize', 'Holiday', 'Timezone',
                'Transaction', 'FirstCard', 'MultiCard', 'InOutFun',
                'TemplateV10'
        """
        if name not in models_registry:
            raise FireError(f"Unknown table '{name}', possible values are: {list(sorted(models_registry.keys()))}")
        qs = self._zk.table(name)
        table_cls = qs._table_cls
        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, table_cls.fields_mapping().keys())
        return Query(qs, ModelConverter(formatter, table_cls))

    def read_raw(self, name: str, *, buffer_size=32768):
        """Return the raw data from a given table.

        ZKAccess device stores the table data in string format,
        sometimes additionally encoded. This command returns the raw
        string data (i.e. how it stores on device).

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
            raise FireError(f"Unknown table '{name}', possible values are: {list(sorted(models_registry.keys()))}")
        table_cls = models_registry[name]
        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, table_cls.fields_mapping().values())
        converter = TextConverter(formatter)
        converter.write_records(self._zk.sdk.get_device_data(table_cls.table_name, [], {}, buffer_size, False))

    def write_raw(self, name: str):
        """Write raw data to a given table.

        ZKAccess device stores the table data in string format,
        sometimes additionally encoded. This command expects the data
        in raw string format (i.e. how it stores on device).

        See also `read_raw` command.

        Args:
            name: table name. Possible values are:
                'User', 'UserAuthorize', 'Holiday', 'Timezone',
                'Transaction', 'FirstCard', 'MultiCard', 'InOutFun',
                'TemplateV10'
        """
        if name not in models_registry:
            raise FireError(f"Unknown table '{name}', possible values are: {list(sorted(models_registry.keys()))}")
        table_cls = models_registry[name]
        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, table_cls.fields_mapping().values())
        converter = TextConverter(formatter)

        gen = self._zk.sdk.set_device_data(table_cls.table_name)
        gen.send(None)
        for record in converter.read_records():
            gen.send(record)

        try:
            gen.send(None)
        except StopIteration:
            pass

    def upload_file(self, remote_filename: str):
        """Upload a data to a remote file on device. By default,
        this command reads stdin, use `--file` cli option to specify
        a source file.

        Args:
            remote_filename: filename on a device to write
        """
        self._zk.upload_file(remote_filename, io.BytesIO(DATA_IN.read().encode()))

    def download_file(self, remote_filename: str):
        """Download a file from a device. By default, this command
        prints data to stdout, use `--file` cli option to specify a
        destination file.

        Args:
            remote_filename: filename on a device to read
        """
        DATA_OUT.write(self._zk.download_file(remote_filename).read().decode())

    def cancel_alarm(self):
        """Switch a device from the alarm mode to the normal mode"""
        self._zk.cancel_alarm()

    @property
    def doors(self) -> Doors:
        """Working with inputs and outputs grouped by doors. Their count
        depends on a device model.

        This command aggregates actions for relays, readers and aux inputs
        related by a selected door or doors.
        """
        return Doors(self._zk.doors)

    @property
    def relays(self):
        """Working with relays. Relays count depends on a device model."""
        return Relays(self._zk.relays)

    @property
    def readers(self):
        """Working with readers. Readers count depends on a device model."""
        return Readers(self._zk.readers)

    @property
    def aux_inputs(self):
        """Working with aux inputs. Aux inputs count depends on a device model."""
        return AuxInputs(self._zk.aux_inputs)

    @property
    def events(self):
        """Working with event log."""
        return Events(self._zk.events)

    @property
    def parameters(self):
        """Working with device parameters. This does not include the door
        parameters, they are available in `doors` command like this
        `... doors 1 parameters`.
        """
        return Parameters(self._zk.parameters)

    def restart(self):
        """Restart a device."""
        self._zk.restart()


class CLI:
    """PyZKAccess command-line interface

    Typical usage:

        Commands for a connected device:
            $ pyzkaccess connect <ip> <subcommand|group> [args] [<subcommand> [args]...]

        Commands not related to a particular device:
            $ pyzkaccess <command> [parameters]

    Every command, group and subcommand has its own help contents, just
    type them and append `--help` at the end.

    Usage examples:

        Getting help for 'connect' command:
            $ pyzkaccess connect --help

        Getting help for 'table'->'where' subcommand:
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

    def __call__(self, *, format: str = "ascii_table", file: str = None, dllpath: str = "plcommpro.dll"):
        if format not in IO_FORMATS:
            # Workaround of "Could not consume arg" message appearing
            # instead of exception message problem
            sys.stderr.write(f"ERROR: Unknown format '{format}', available are: {list(sorted(IO_FORMATS.keys()))}\n")
            raise FireError(f"Unknown format '{format}', available are: {list(sorted(IO_FORMATS.keys()))}")

        global OPT_IO_FORMAT
        OPT_IO_FORMAT = format

        self._file = None
        if file:
            d = os.path.dirname(file)
            if not os.path.isdir(d):
                # Workaround of "Could not consume arg" message appearing
                # instead of exception message problem
                sys.stderr.write(f"ERROR: Directory '{d}' does not exist\n")
                raise FireError(f"Directory {d} does not exist")

            self._file = open(file, "r+")
            self._file.seek(0)

            global DATA_IN
            global DATA_OUT
            DATA_IN = self._file
            DATA_OUT = WriteFile(self._file)

        self._dllpath = dllpath

        return self

    def setup(self, *, yes: bool = False, path: str = None) -> None:
        """Convenience command to setup the pyzkaccess running environment.

        This command checks the OS settings and the PULL SDK installation
        status (and suggests to download and install it if not found).

        It is recommended to run this command before using other commands.

        Args:
            yes (bool): assume yes for all questions. Default is False
            path (str): URL, path to zip or path to directory with PULL SDK dll files.
        """
        sys.stdout.write("Setting up the environment...\n")
        setup(not yes, path)

    def connect(self, ip: str, *, model: str = "ZK400") -> ZKCommand:
        """
        Connect to a device.

        IP argument can be a string with an IPv4 address or "ENV" to get options from environment variables.

        Environment variables:

            PYZKACCESS_CONNECT_IP or PYZKACCESS_CONNECT_CONNSTR: IPv4 address or the whole connection string
                Connection string example: 'protocol=TCP,ipaddress=192.168.1.201,port=4370,timeout=4000,passwd='
            PYZKACCESS_CONNECT_MODEL: device model. Possible values are: ZK100, ZK200, ZK400

        Args:
            ip (str): IPv4 address or "ENV" to get options from environment variables
            model (DeviceModels): device model. Possible values are:
                ZK100, ZK200, ZK400
        """
        # Hack: prevent making a connection if help is requested
        if "--help" in sys.argv or "-h" in sys.argv:
            return ZKCommand(ZKAccess(None, device_model=ZK400, dllpath=self._dllpath))

        connstr = None

        if not ip:
            raise FireError("IP argument is required")

        if ip == "ENV":
            connstr = os.getenv("PYZKACCESS_CONNECT_CONNSTR")
            if not connstr:
                ip = os.getenv("PYZKACCESS_CONNECT_IP")
                if not ip:
                    raise FireError("IP address and connection string are not set in the environment variables")

            if m := os.getenv("PYZKACCESS_CONNECT_MODEL"):
                model = m

        device_model = DEVICE_MODELS.get(model)
        if device_model is None:
            raise FireError(f"Unknown device model '{model}', possible values are: ZK100, ZK200, ZK400")

        if not connstr:
            connstr = f"protocol=TCP,ipaddress={self._parse_ip(ip)},port=4370,timeout=4000,passwd="

        zkcmd = ZKCommand(ZKAccess(connstr, device_model=device_model, dllpath=self._dllpath))

        return zkcmd

    def search_devices(self, *, broadcast_address: str = "255.255.255.255"):
        """
        Scan the local network for active C3 devices

        Args:
            broadcast_address: Broadcast IP to use. Default: 255.255.255.255
        """
        headers = ["mac", "ip", "serial_number", "model", "version"]
        formatter = BaseFormatter.get_formatter(OPT_IO_FORMAT)(DATA_IN, DATA_OUT, headers)
        converter = TextConverter(formatter)

        def _search_devices():
            devices = ZKAccess.search_devices(self._parse_ip(broadcast_address), dllpath=self._dllpath)
            for device in devices:
                values = [device.mac, device.ip, device.serial_number, device.model.name, device.version]
                yield dict(zip(headers, values))

        converter.write_records(_search_devices())

    def change_ip(self, mac_address: str, new_ip: str, *, broadcast_address: str = "255.255.255.255"):
        """Reset the device's IP address by its MAC address.

        For security reasons, the network settings can be reset by this command
        on devices with no password set.

        Args:
            mac_address: MAC address of a device
            new_ip: new IPv4 address to be set
            broadcast_address: broadcast network address to send
                broadcast packets to. Default: 255.255.255.255
        """
        ZKAccess.change_ip(
            self._parse_mac(mac_address),
            self._parse_ip(new_ip),
            self._parse_ip(broadcast_address),
            ChangeIPProtocol.udp,
            self._dllpath,
        )

    @staticmethod
    def _parse_ip(value: Any) -> str:
        try:
            if not isinstance(value, str):  # python-fire may pass here int, tuple, etc.
                raise ValueError("Bad IPv4 address")
            ip_addr = ipaddress.ip_address(value)
        except ValueError:
            raise FireError(f"Bad IPv4 address: '{value}'")

        return str(ip_addr)

    @staticmethod
    def _parse_mac(value: Any) -> str:
        if not isinstance(value, str):
            raise FireError("Bad MAC address")

        if not re.match(r"^[0-9a-fA-F]{2}([:-]?[0-9a-fA-F]{2}){5}$", value):
            raise FireError(f"Bad MAC address '{value}'")

        return value


class WriteFile(wrapt.ObjectProxy):
    """Wrapper around a file-like object which truncates file to a
    current position on flush
    """

    def flush(self):
        self.__wrapped__.truncate()
        self.__wrapped__.flush()


def main():
    cli = CLI()
    try:
        fire.Fire(cli)
    except UnsupportedPlatformError:
        sys.stderr.write(f"ERROR: Platform {sys.platform} is not supported\n")
        sys.exit(5)
    except Exception as e:
        if not isinstance(e, ZKSDKError):
            sys.stderr.write(traceback.format_exc())
        sys.stderr.write(
            f"ERROR: {e}\n"
            f"Note: You can ensure that the environment is set up correctly by running the `pyzkaccess setup` command\n"
        )
        sys.exit(2)

    if cli._file is not None:
        cli._file.close()


if __name__ == "__main__":
    main()
