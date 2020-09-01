from .relay import RelayGroup


class ZKModel:
    """Base class for concrete ZK model"""
    name = None
    relays = None
    relays_def = None
    groups_def = None
    readers_def = None


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


class ZK200(ZKModel):
    """ZKAccess C3-200"""
    name = 'C3-200'
    relays = 4
    relays_def = (1, 2, 1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.aux, RelayGroup.lock, RelayGroup.lock)
    readers_def = (1, 2)


class ZK100(ZKModel):
    """ZKAccess C3-100"""
    name = 'C3-100'
    relays = 2
    relays_def = (1, 2)
    groups_def = (RelayGroup.aux, RelayGroup.lock)
    readers_def = (1, )


class ZKDevice:
    __slots__ = ('mac', 'ip', 'serial_number', 'model', 'version')
    available_models = (ZK100, ZK200, ZK400)

    def __init__(self, s=None):
        if s:
            self.parse(s)

    def parse(self, device_line: str) -> None:
        if device_line in ('', '\r\n'):
            raise ValueError("Empty event string")

        tokens = {
            'MAC': 'mac',
            'IP': 'ip',
            'SN': 'serial_number',
            'Device': 'model',
            'Ver': 'version'
        }

        pieces = device_line.split(',')
        for piece in pieces:
            tok, val = piece.split('=')
            if tok not in tokens:
                raise ValueError("Unknown param '{}={}' found in device string".format(tok, val))
            setattr(self, tokens.pop(tok), val)

        if tokens:
            raise ValueError("Parameters {} are not found in device string".format(tokens.keys()))

        self.model = self._get_model_cls(self.model)

    def _get_model_cls(self, model_name):
        for cls in self.available_models:
            if cls.name == model_name:
                return cls

        raise ValueError("Unknown device model '{}'".format(model_name))

    def __str__(self):
        params = ', '.join('{}={}'.format(k, getattr(self, k, '?')) for k in self.__slots__)
        return 'Device[{}]({})'.format(self.model.name, params)

    def __repr__(self):
        return self.__str__()
