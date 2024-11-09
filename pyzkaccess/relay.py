__all__ = ["Relay", "RelayList"]

from abc import ABCMeta, abstractmethod
from typing import Any, Iterable, TypeVar, Union, overload

from pyzkaccess.common import UserTuple
from pyzkaccess.enums import ControlOperation, RelayGroup
from pyzkaccess.sdk import ZKSDK


class RelayInterface(metaclass=ABCMeta):
    @abstractmethod
    def switch_on(self, timeout: int) -> None:
        """Switch on a relay for the given time. If a relay is already
        switched on then the time will start to count from the
        beginning.

        Args:
            timeout (int): time in seconds a relay being enabled.
                A number between 0 and 255
        """


class Relay(RelayInterface):
    """A relay"""

    def __init__(self, sdk: ZKSDK, group: RelayGroup, number: int):
        self.group = group
        self.number = number
        self._sdk = sdk

    def switch_on(self, timeout: int) -> None:
        """Switch on a relay for the given time. If a relay is already
        switched on then the time will start to count from the
        beginning.

        Args:
            timeout (int): time in seconds a relay being enabled.
                A number between 0 and 255
        """
        if timeout < 0 or timeout > 255:
            raise ValueError(f"Timeout must be in range 0..255, got {timeout}")

        self._sdk.control_device(ControlOperation.output.value, self.number, self.group.value, timeout, 0)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Relay):
            return self.number == other.number and self.group == other.group and self._sdk is other._sdk
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f"Relay.{self.group.name}({self.number})"

    def __repr__(self) -> str:
        return f"Relay(RelayGroup.{self.group.name}, {self.number})"


_RelayListT = TypeVar("_RelayListT", bound="RelayList")


class RelayList(RelayInterface, UserTuple[Relay]):
    """Relay collection for group operations"""

    def __init__(self, sdk: ZKSDK, relays: Iterable[Relay] = ()):
        super().__init__(relays)
        self._sdk = sdk

    def switch_on(self, timeout: int) -> None:
        """Switch on a relay for the given time. If a relay is already
        switched on then the time will start to count from the
        beginning.

        Args:
            timeout (int): time in seconds a relay being enabled.
                A number between 0 and 255
        """
        if timeout < 0 or timeout > 255:
            raise ValueError(f"Timeout must be in range 0..255, got {timeout}")

        for relay in self:
            self._sdk.control_device(ControlOperation.output.value, relay.number, relay.group.value, timeout, 0)

    @property
    def aux(self) -> "RelayList":
        """Return relays only from aux group"""
        relays = [x for x in self if x.group == RelayGroup.aux]
        return self.__class__(sdk=self._sdk, relays=relays)

    @property
    def lock(self) -> "RelayList":
        """Return relays only from lock group"""
        relays = [x for x in self if x.group == RelayGroup.lock]
        return self.__class__(sdk=self._sdk, relays=relays)

    @overload
    def __getitem__(self, item: int) -> Relay: ...

    @overload
    def __getitem__(self: _RelayListT, item: slice) -> _RelayListT: ...

    def __getitem__(self: _RelayListT, item: Union[int, slice]) -> Union[Relay, _RelayListT]:
        if isinstance(item, slice):
            return self.__class__(self._sdk, relays=self.data[item])

        return self.data[item]

    def by_mask(self, mask: Iterable[Any]) -> "RelayList":
        """Return only relays starting from 0 which are matched by given
        mask. Mask can be any iterable with objects that can be truthy/falsy.

        E.g. for mask `[1, 0, 0, 1, 0, 0, 1, 0]` this function
        returns 1, 4 and 7 relays of all eight relays.

        If a mask covers more items than a device has relays, the rest
        mask values will be dropped off. For example, for device with
        4 relays, the mask `[1, 0, 0, 1, 0, 0, 1, 0]` will return only
        relay 1.

        If mask is smaller than count of relays on a device, then the
        rest relays are don't be considered. For example, for device
        of 8 relays, a mask `[1, 0, 0]` will return only relay 1.

        Args:
            mask (Iterable[Any]): mask is a list of
                ints or bools

        Returns:
          RelayList: new instance of RelayList contained needed relays

        """
        relays = [x for x, m in zip(self, mask) if m]
        return self.__class__(sdk=self._sdk, relays=relays)
