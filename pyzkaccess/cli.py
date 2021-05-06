import abc
import csv
import sys
from datetime import date, time, datetime
from enum import Enum
from typing import Type, Any, Iterable, TextIO, Mapping, Generator, Set, Union, KeysView

import fire
from fire.core import FireError

from pyzkaccess import ZKAccess, ZK100, ZK200, ZK400
from pyzkaccess.device_data.model import models_registry, Model
from pyzkaccess.device_data.queryset import QuerySet
from pyzkaccess.param import DaylightSavingMomentMode1, DaylightSavingMomentMode2
from pyzkaccess.door import Door

device_models = {'ZK100': ZK100, 'ZK200': ZK200, 'ZK400': ZK400}

opt_io_format = 'csv'
opt_headers = True
data_in = sys.stdin
data_out = sys.stdout


class BaseFormatter(metaclass=abc.ABCMeta):
    class WriterInterface(metaclass=abc.ABCMeta):
        @abc.abstractmethod
        def write(self, record: Mapping[str, str]) -> None:
            pass

        @abc.abstractmethod
        def flush(self) -> None:
            pass

    def __init__(self, istream: TextIO, ostream: TextIO):
        self._istream = istream
        self._ostream = ostream

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
    class CSVWriter(BaseFormatter.WriterInterface):
        def __init__(self, ostream: TextIO):
            self._ostream = ostream
            self._writer = None

        def write(self, record: Mapping[str, str]) -> None:
            if self._writer is None:
                self._writer = csv.DictWriter(self._ostream, record.keys())
                self._writer.writeheader()

            self._writer.writerow(record)

        def flush(self) -> None:
            pass

    def get_reader(self) -> Iterable[Mapping[str, str]]:
        return csv.DictReader(self._istream)

    def get_writer(self) -> BaseFormatter.WriterInterface:
        return CSVFormatter.CSVWriter(self._ostream)


io_formats = {
    'csv': CSVFormatter
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
    def read_records(self) -> Generator[Mapping[str, Any], None, None]:
        for item in self._formatter.get_reader():
            yield item

    def write_records(self, records: Iterable[Mapping[str, Any]]):
        writer = self._formatter.get_writer()
        for item in records:
            writer.write(item)

        writer.flush()


class TypedFieldConverter(BaseConverter):
    TUPLE_SEPARATOR = ','

    def __init__(self, formatter: BaseFormatter, field_types: Mapping[str, Type], *args, **kwargs):
        super().__init__(formatter, *args, **kwargs)
        self._field_types = field_types

    def read_records(self) -> Generator[Mapping[str, Any], None, None]:
        for item in self._formatter.get_reader():
            # Convert a text field value to a typed value
            yield {fname: self._to_field_value(fval, self._field_types.get(fname, str))
                   for fname, fval in item.items()}

    def write_records(self, records: Iterable[Mapping[str, Any]]):
        writer = self._formatter.get_writer()
        for item in records:
            # Convert a typed field value to a string value
            record = {fname: self._to_string_value(fval, self._field_types.get(fname, str))
                      for fname, fval in item.items()}
            writer.write(record)

        writer.flush()

    def _to_field_value(self, value: str, field_datatype: Type) -> Any:
        return self._input_converters[field_datatype](value)

    def _to_string_value(self, value: Any, field_datatype: Type) -> str:
        return self._output_converters[field_datatype](value)

    @staticmethod
    def _parse_enum(value: str) -> Enum:
        try:
            res = Enum(value)
        except ValueError:
            res = Enum(int(value))

        return res

    @staticmethod
    def _parse_tuple(value: str) -> tuple:
        return tuple(value.split(TypedFieldConverter.TUPLE_SEPARATOR))

    @staticmethod
    def _out_tuple(value: tuple) -> str:
        T = TypedFieldConverter  # noqa
        return T.TUPLE_SEPARATOR.join(T._output_converters[type(x)](x) for x in value)

    @staticmethod
    def _parse_daylight_saving_moment_mode1(value: str) -> DaylightSavingMomentMode1:
        args = [int(x) for x in TypedFieldConverter._parse_tuple(value)]
        if len(args) != 4:
            raise ValueError('Daylight saving moment value must contain 4 integers')
        return DaylightSavingMomentMode1(*args)

    @staticmethod
    def _parse_daylight_saving_moment_mode2(value: str) -> DaylightSavingMomentMode2:
        args = [int(x) for x in TypedFieldConverter._parse_tuple(value)]
        if len(args) != 7:
            raise ValueError('Daylight saving moment value must contain 7 integers')

        is_daylight = bool(args[5])
        buffer_size = args[6]
        res = DaylightSavingMomentMode2(None, is_daylight, buffer_size)
        for ind, attr in enumerate(('month', 'week_of_month', 'day_of_week', 'hour', 'minute')):
            setattr(res, attr, args[ind])

        return res

    @staticmethod
    def _out_daylight_saving_moment_mode2(value: DaylightSavingMomentMode2) -> str:
        res = [
            str(getattr(value, attr))
            for attr in ('month', 'week_of_month', 'day_of_week', 'hour', 'minute')
        ]
        res.extend((str(int(value.is_daylight)), str(value.buffer_size)))
        return TypedFieldConverter.TUPLE_SEPARATOR.join(res)

    # The following converters parses string value respresentation from
    # stdin and converts to a field value
    _input_converters = {
        str: lambda x: str(x),
        bool: lambda x: bool(int(x)),
        int: int,
        tuple: _parse_tuple,
        date: lambda x: datetime.strptime(x, '%Y-%m-%d').date(),
        time: lambda x: datetime.strptime(x, '%H:%M:%S').time(),
        datetime: lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'),
        Enum: _parse_enum,
        DaylightSavingMomentMode1: _parse_daylight_saving_moment_mode1,
        DaylightSavingMomentMode2: _parse_daylight_saving_moment_mode2
    }

    # The following functions converts field values to their string
    # representation suitable for stdout output
    _output_converters = {
        str: lambda x: str(x),
        bool: lambda x: str(int(x)),
        int: str,
        tuple: _out_tuple,
        date: lambda x: x.strftime('%Y-%m-%d'),
        time: lambda x: x.strftime('%H:%M:%S'),
        datetime: lambda x: x.strftime('%Y-%m-%d %H:%M:%S'),
        Enum: lambda x: str(x.value),
        DaylightSavingMomentMode1: lambda x: TypedFieldConverter.TUPLE_SEPARATOR.join(
            str(getattr(x, attr)) for attr in ('month', 'day', 'hour', 'minute')
        ),
        DaylightSavingMomentMode2: _out_daylight_saving_moment_mode2
    }


class ModelConverter(TypedFieldConverter):
    TUPLE_SEPARATOR = ','

    def __init__(self, formatter: BaseFormatter, model_cls: Type[Model], *args, **kwargs):
        field_types = {k: getattr(model_cls, k).field_datatype
                       for k in model_cls.fields_mapping().keys()}
        super().__init__(formatter, field_types, *args, **kwargs)
        self._model_cls = model_cls

    def read_records(self) -> Generator[Mapping[str, Any], None, None]:
        for item in self._formatter.get_reader():
            model_dict = self.to_model_dict(item)
            yield model_dict

    def write_records(self, records: Iterable[Mapping[str, Any]]):
        writer = self._formatter.get_writer()
        for item in records:
            record = self.to_raw_dict(item)
            writer.write(record)

        writer.flush()

    def to_model_dict(self, record: Mapping[str, str]) -> Mapping[str, Any]:
        model_fields = {k: getattr(self._model_cls, k)
                        for k in self._model_cls.fields_mapping().keys()}

        self._validate_field_names(model_fields.keys(), record)

        # Convert dict with text values to a model dict with typed values
        return {fname: self._to_field_value(fval, model_fields[fname].field_datatype)
                for fname, fval in record.items()}

    def to_raw_dict(self, model_dict: Mapping[str, Any]) -> Mapping[str, str]:
        model_fields = {k: getattr(self._model_cls, k)
                        for k in self._model_cls.fields_mapping().keys()}

        self._validate_field_names(model_fields.keys(), model_dict)

        # Convert model dict values to a text values
        return {fname: self._to_string_value(fval, model_fields[fname].field_datatype)
                for fname, fval in model_dict.items()}

    def _validate_field_names(self, fields: Union[Set[str], KeysView], item: Mapping[str, Any]):
        # Check if field names are all exist in the model
        extra_fields = item.keys() - fields
        if extra_fields:
            raise FireError("Unknown fields of {} found in the input data: {}".format(
                self._model_cls.__name__, list(sorted(extra_fields))
            ))


class Query:
    def __init__(self, qs: QuerySet, io_converter: ModelConverter):
        self._qs = qs
        self._io_converter = io_converter

    def __call__(self):
        if self._qs is not None:
            self._io_converter.write_records(list(self._qs))

    def where(self, **conditions) -> 'Query':
        typed_conditions = self._io_converter.to_model_dict(conditions)
        self._qs = self._qs.where(**typed_conditions)

        return self

    def upsert(self):
        headers = None
        items = []
        for line in self._io_converter.read_records():
            if opt_headers and headers is None:
                headers = line
                continue
            items.append({k: v for k, v in zip(headers, line)})

        self._qs.upsert(items)
        self._qs = None

    def delete(self):
        headers = None
        items = []
        for line in self._io_converter.read_records():
            if opt_headers and headers is None:
                headers = line
                continue
            items.append({k: v for k, v in zip(headers, line)})

        self._qs.delete(items)
        self._qs = None

    def delete_all(self):
        self._qs.delete_all()
        self._qs = None

    def count(self):
        res = self._qs.count()
        self._qs = None
        return res


class Doors:
    def __init__(self, items):
        self._items = items

    def relays(self):
        return Relays(self._items.relays)

    def readers(self):
        if isinstance(self._items, Door):
            return Readers(self._items.reader)
        return Readers(self._items.readers)

    def aux_inputs(self):
        if isinstance(self._items, Door):
            return AuxInputs(self._items.aux_input)
        return AuxInputs(self._items.aux_inputs)

    def parameters(self):
        if isinstance(self._items, Door):
            return Parameters(self._items.parameters)
        raise FireError('Parameters may be used only for single door')

    def events(self):
        return Events(self._items.events)


class Relays:
    def __init__(self, items):
        self._items = items

    def switch_on(self, *, timeout=5):
        self._items.switch_on(timeout)


class Readers:
    def __init__(self, items):
        self._items = items

    def events(self):
        return Events(self._items.events)


class AuxInputs:
    def __init__(self, items):
        self._items = items

    def events(self):
        return Events(self._items.events)


class Events:
    def __init__(self, event_log):
        self._event_log = event_log

    def __call__(self):
        formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out)
        converter = TextConverter(formatter)
        converter.write_records({s: getattr(ev, s) for s in ev.__slots__} for ev in self._event_log)

    def poll(self, timeout=60):
        events = self._event_log.poll(timeout)
        if events:
            formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out)
            converter = TextConverter(formatter)
            converter.write_records({s: getattr(ev, s) for s in ev.__slots__} for ev in events)


class Parameters:
    def __init__(self, item):
        self._item = item
        item_cls = item.__class__
        self._param_list = {attr for attr in dir(item_cls)
                            if isinstance(getattr(item_cls, attr), property)}
        # Extract types from getters annotations. Skip if no getter
        # Assume str if no return annotation has set
        props = {attr: getattr(item_cls, attr) for attr in self._param_list
                 if getattr(item_cls, attr).fget is not None}
        self._prop_types = {k: getattr(v.fget, '__annotations__', {}).get('return', str)
                            for k, v in props.items()}

        self._formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out)
        self._converter = TypedFieldConverter(self._formatter, self._prop_types)

    def __call__(self, names):
        if isinstance(names, str):
            names = (names, )
        elif not isinstance(names, (list, tuple)):
            raise FireError("Names must be a name or list of parameters")

        names = set(names)

        extra_names = names - set(self._param_list)
        if extra_names:
            raise FireError('Unknown parameters were given: {}'.format(extra_names))

        self._converter.write_records(
            {'parameter_name': name, 'value': getattr(self._item, name)} for name in sorted(names)
        )

    def list(self):
        formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out)
        converter = TypedFieldConverter(formatter, self._prop_types)
        converter.write_records({'parameter_name': x} for x in sorted(self._param_list))

    def set(self, **values):
        if values:
            self._set_from_args(values)
        else:
            self._set_from_input()

    def _set_from_input(self):
        for record in self._converter.read_records():
            if not ({'parameter_name', 'value'} & record.keys()):
                raise FireError('Items')

            setattr(self._item, record['parameter_name'], record['value'])

    def _set_from_args(self, args: dict):
        extra_names = args.keys() - set(self._param_list)
        if extra_names:
            raise FireError('Unknown parameters were given: {}'.format(extra_names))

        for name, val in args.items():
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
            raise FireError(
                "Unknown table '{}', possible values are User, UserAuthorize, "
                "Holiday, Timezone, Transaction, FirstCard, MultiCard, "
                "InOutFun, TemplateV10".format(name)
            )
        qs = self._zk.table(name)
        formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out)
        return Query(qs, ModelConverter(formatter, qs._table_cls))

    def doors(self, *, numbers=None) -> Doors:
        item = self._parse_array_index(numbers)
        return Doors(self._zk.doors[item])

    def relays(self, *, numbers=None):
        item = self._parse_array_index(numbers)
        return Relays(self._zk.relays[item])

    def readers(self, *, numbers=None):
        item = self._parse_array_index(numbers)
        return Readers(self._zk.readers[item])

    def aux_inputs(self, *, numbers=None):
        item = self._parse_array_index(numbers)
        return AuxInputs(self._zk.aux_inputs[item])

    def events(self):
        return Events(self._zk.events)

    def parameters(self):
        return Parameters(self._zk.parameters)

    def restart(self):
        self._zk.restart()

    @staticmethod
    def _parse_array_index(opt_indexes):
        if opt_indexes is None:
            return slice(None, None)
        if isinstance(opt_indexes, (list, tuple)):
            start = opt_indexes[0] if opt_indexes else None
            stop = opt_indexes[1] if len(opt_indexes) > 1 else None
            return slice(start, stop)
        if isinstance(opt_indexes, int):
            return opt_indexes

        raise FireError("Numbers must be list or int")


class CLI:
    @staticmethod
    def connect(ip: str, *, model: str = 'ZK400') -> ZKCommand:
        """
        PyZKAccess command-line interface

        Typical usage: pyzkaccess <ip> command1 [parameters] command2 [parameters] ...

        Args:
            ip (str): IP address of a device
            model (DeviceModels): device model. Possible values are: ZK100, ZK200, ZK400
        """
        model = device_models.get(model)
        if model is None:
            raise FireError(
                "Unknown device model '{}', possible values are: ZK100, ZK200, ZK400".format(model)
            )

        if not ip:
            raise FireError('IP argument is required')

        connstr = 'protocol=TCP,ipaddress={},port=4370,timeout=4000,passwd='.format(ip)

        zkcmd = ZKCommand(ZKAccess(connstr, device_model=model))

        return zkcmd

    @staticmethod
    def search_devices(*, broadcast_address: str = '255.255.255.255'):
        formatter = BaseFormatter.get_formatter(opt_io_format)(data_in, data_out)
        converter = TextConverter(formatter)

        devices = ZKAccess.search_devices(broadcast_address)
        out = []
        for device in devices:
            out.append({
                'mac': device.mac,
                'ip': device.ip,
                'serial_number': device.serial_number,
                'model': device.model.name,
                'version': device.version
            })
        converter.write_records(out)


def main():
    fire.Fire(CLI())


if __name__ == '__main__':
    main()

# TODO: warning about SDK linux systems