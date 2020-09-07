__all__ = [
    'Relay',
    'RelayList'
]

from abc import ABCMeta, abstractmethod
from typing import Iterable, Union

from .common import UserTuple
from .enum import RelayGroup, ControlOperation
from .sdk import ZKSDK


class RelayInterface(metaclass=ABCMeta):
    @abstractmethod
    def switch_on(self, timeout: int) -> None:
        """
        Switch on a relay for the given time. If a relay is already
        switched on then its timeout will be refreshed
        :param timeout: timeout in seconds, Number between 0 and 255
        :return:
        """
        pass


class Relay(RelayInterface):
    """Concrete relay"""
    def __init__(self, sdk: ZKSDK, group: RelayGroup, number: int):
        self.group = group
        self.number = number
        self._sdk = sdk

    def switch_on(self, timeout: int) -> None:
        """
        Switch on a relay for the given time. If a relay is already
        switched on then its timeout will be refreshed
        :param timeout: Timeout in seconds while relay will be enabled.
         Number between 0 and 255
        :return:
        """
        if timeout < 0 or timeout > 255:
            raise ValueError("Timeout must be in range 0..255, got {}".format(timeout))

        self._sdk.control_device(
            ControlOperation.output.value,
            self.number,
            self.group.value,
            timeout,
            0
        )

    def __eq__(self, other):
        if isinstance(other, Relay):
            return self.number == other.number \
                   and self.group == other.group \
                   and self._sdk is other._sdk
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "Relay.{}({})".format(self.group.name, self.number)

    def __repr__(self):
        return "Relay(RelayGroup.{}, {})".format(self.group.name, self.number)


class RelayList(RelayInterface, UserTuple):
    """Collection of relay objects which is used to perform group
    operations over multiple relays
    """
    def __init__(self, sdk: ZKSDK, relays: Iterable[Relay] = ()):
        super().__init__(relays)
        self._sdk = sdk

    def switch_on(self, timeout: int) -> None:
        """
        Switch on all relays in set for a given time
        :param timeout: Timeout in seconds while relay will be enabled.
         Number between 0 and 255
        :return:
        """
        if timeout < 0 or timeout > 255:
            raise ValueError("Timeout must be in range 0..255, got {}".format(timeout))

        for relay in self:
            self._sdk.control_device(ControlOperation.output.value,
                                     relay.number,
                                     relay.group.value,
                                     timeout,
                                     0)

    @property
    def aux(self) -> 'RelayList':
        """Return relays only from aux group"""
        relays = [x for x in self if x.group == RelayGroup.aux]
        return self.__class__(sdk=self._sdk, relays=relays)

    @property
    def lock(self) -> 'RelayList':
        """Return relays only from lock group"""
        relays = [x for x in self if x.group == RelayGroup.lock]
        return self.__class__(sdk=self._sdk, relays=relays)

    def __getitem__(self, item):
        relays = self.data[item]
        if isinstance(item, slice):
            return self.__class__(self._sdk, relays=relays)
        else:
            return relays

    def by_mask(self, mask: Iterable[Union[int, bool]]) -> 'RelayList':
        """
        Return only relays starting from 0 which are matched by given
        mask. E.g. for `mask=[1, 0, 0, 1, 0, 0, 1, 0]` the function
        returns the 1st, the 4th and the 7th of 8 relays.

        If mask is longer than count of relays, the rest values
        will be ignored:
        for 5 relays `mask=[1, 0, 0, 1, 0, 0, 1, 0]` will return
        the 1st and the 4th relays.

        If mask is shorter than count of relays then the rest relays
        will be ignored:
        for 8 relays `mask=[1, 0, 0]` will return the 1st relay only.
        :param mask: mask is a list of ints or bools
        :return: new instance of RelayList contained needed relays
        """
        relays = [x for x, m in zip(self, mask) if m]
        return self.__class__(sdk=self._sdk, relays=relays)
