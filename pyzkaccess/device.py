__all__ = [
    'ZKModel',
    'ZK100',
    'ZK200',
    'ZK400',
    'ZKDevice'
]
from typing import Mapping, Optional

from .common import DocDict
from .enum import RelayGroup


class ZKModel:
    """Base class for concrete ZK model Contains model-specific
    definitions
    """
    #: Name of model
    name = None

    #: Relays count
    relays = None

    #: Definition of relay numbers (count must be equal to `relays`)
    relays_def = None

    #: Definition of relay groups (count must be equal to `relays`)
    groups_def = None

    #: Definition of reader numbers
    readers_def = None

    #: Definition of door numbers
    doors_dev = None

    #: Definition of aux input numbers
    aux_inputs_def = None

    #: Anti-passback rules available on concrete device model
    anti_passback_rules = None

    #: Interlock rules available on concrete device model
    interlock_rules = None


class ZK400(ZKModel):
    """ZKAccess C3-400 model"""
    name = 'C3-400'
    relays = 8
    relays_def = (
        1, 2, 3, 4,
        1, 2, 3, 4
    )
    groups_def = (
        RelayGroup.aux, RelayGroup.aux, RelayGroup.aux, RelayGroup.aux,
        RelayGroup.lock, RelayGroup.lock, RelayGroup.lock, RelayGroup.lock
    )
    readers_def = (1, 2, 3, 4)
    doors_def = (1, 2, 3, 4)
    aux_inputs_def = (1, 2, 3, 4)
    anti_passback_rules = DocDict({
        0:   'Anti-passback disabled',
        1:   'Enable the anti-passback function Door 1 and Door 2',
        2:   'Enable the anti•passback function between Door 3 and Door 4',
        3:   'Enable the anti-passback function between Door 1 and Door 2, and between '
             'Door 3 and Door 4',
        4:   'Enable the anti-passback function between Door 1,2 and Door 3,4',
        5:   'Enable the anti-passback function between Door 1 and Door 2,3',
        6:   'Enable the anti-passback function between Door 1 and Door 2,3,4',
        16:  'Anti-passback is supported only between the readers of Door 1',
        32:  'Anti-passback is supported only between the readers of Door 2',
        64:  'Anti-passback is supported only between the readers of Door 3',
        128: 'Anti-passback is supported only between the readers of Door 4',
        96:  'Anti-passback is supported concurrently among Door 2 and Door 3 readers respectively',
        160: 'Anti-passback is supported concurrently among Door 2 and Door 4 readers respectively',
        196: 'Anti-passback is supported concurrently among Door 3 and Door 4 readers respectively',
        112: 'Anti-passback is supported concurrently among Door 1, 2, 3 readers respectively',
        176: 'Anti-passback is supported concurrently among Door 1, 2, 4 readers respectively',
        208: 'Anti-passback is supported concurrently among Door 1, 3, 4 readers respectively',
        224: 'Anti-passback is supported concurrently among Door 2, 3, 4 readers respectively',
        240: 'Anti-passback is supported concurrently among Door 1, 2, 3, 4 readers respectively',
    })
    interlock_rules = DocDict({
        0: 'Interlock disabled',
        1: 'Interlock Door 1 and Door 2 mutually',
        2: 'Interlock Door 3 and Door 4 mutually',
        3: 'Interlock Door 1, Door 2 and Door 3 mutually',
        4: 'Interlock Door 1 and Door 2 mutually and interlock Door 3 and Door 4 mutually',
        5: 'Interlock Door 1, Door 2, Door 3, Door 4 mutually',
    })


class ZK200(ZKModel):
    """ZKAccess C3-200"""
    name = 'C3-200'
    relays = 4
    relays_def = (1, 2, 1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.aux, RelayGroup.lock, RelayGroup.lock)
    readers_def = (1, 2)  # FIXME: fix ZKAccess.doors for C3-200
    doors_def = (1, 2)
    aux_inputs_def = (1, 2)
    anti_passback_rules = DocDict({
        0: 'Anti-passback disabled',
        1: 'Enable the anti-passback function between Door 1 and Door 2 (one-way) '
           'or readers of Door 1 (two-way)',
        2: 'Enable the anti-passback function between readers of Door 2 (two-way)',
        3: 'Enable the anti-passback function between readers of Door 1 and between readers of '
           'Door 2 respectively (two-way)',
        4: 'Enable the anti-passback function between Door 1 and Door 2 (two-way)'
    })
    interlock_rules = DocDict({
        0: 'Interlock disabled',
        1: 'Interlock Door 1 and Door 2 mutually',
    })


class ZK100(ZKModel):
    """ZKAccess C3-100"""
    name = 'C3-100'
    relays = 2
    relays_def = (1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.lock)
    readers_def = (1, )  # FIXME: fix ZKAccess.doors for C3-100
    doors_def = (1, )
    aux_inputs_def = (1, )  # FIXME: fix ZKAccess.doors for C3-100
    anti_passback_rules = DocDict({
        0: 'Anti-passback disabled',
        1: 'Enable the anti-passback function between the readers of Door1 (two-way)',
    })
    interlock_rules = DocDict({
        0: 'Interlock disabled',
    })


class ZKDevice:
    """Concrete ZK device info"""
    __slots__ = ('mac', 'ip', 'serial_number', 'model', 'version')
    parse_tokens = ('MAC', 'IP', 'SN', 'Device', 'Ver')  # The same order as __slots__
    available_models = (ZK100, ZK200, ZK400)

    def __init__(self, s=None, **params):
        if s is not None:
            params = self.parse(s)

        if not params:
            raise TypeError('You must specify device string or object attributes as kwargs')

        self.mac = params['mac']  # type: Optional[str]
        self.ip = params['ip']  # type: str
        self.serial_number = params['serial_number']  # type: str
        self.model = self._get_model_cls(params['model'])  # type: type(ZKModel)
        self.version = params['version']  # type: Optional[str]

    def parse(self, device_line: str) -> Mapping[str, str]:
        """
        Parse and validate raw device string
        :param device_line: event string
        :return: dictionary where keys are slots and values are
         appropriate values extracted from string
        """
        device_line = device_line.replace('\r\n', '')

        res = {}
        tokens_mapping = dict(zip(self.parse_tokens, self.__slots__))
        pieces = device_line.split(',')
        for piece in pieces:
            tok, val = piece.split('=')
            if tok not in tokens_mapping:
                raise ValueError("Unknown param '{}={}' found in device string '{}'".format(
                    tok, val, device_line
                ))
            res[tokens_mapping[tok]] = val  # {slot: value}

        if res.keys() != set(self.__slots__):
            raise ValueError("Some keys was not found in device string '{}'".format(device_line))

        return res

    def _get_model_cls(self, model_name) -> type(ZKModel):
        if isinstance(model_name, type) and issubclass(model_name, ZKModel):
            return model_name

        for cls in self.available_models:
            if cls.name == model_name:
                return cls

        raise ValueError("Unknown device model '{}'".format(model_name))

    def __eq__(self, other):
        if isinstance(other, ZKDevice):
            return all(getattr(self, attr) == getattr(other, attr) for attr in self.__slots__)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        params = ', '.join('{}={}'.format(k, getattr(self, k, '?')) for k in self.__slots__)
        return 'Device[{}]({})'.format(self.model.name, params)

    def __repr__(self):
        return self.__str__()
