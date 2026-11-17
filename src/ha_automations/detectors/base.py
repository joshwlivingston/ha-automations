"""Detector protocol and the reading it returns."""
from collections.abc import Callable
from typing import NamedTuple, Protocol


class Reading(NamedTuple):
    """A detector's level and direction."""

    level: float | None
    """Level in the detector's units. None if unavailable."""
    rising: bool | None
    """True if the level is rising. None if unknown."""


class Detector(Protocol):
    """Source of a light level for a fade."""

    label: str
    """What the detector measures, for logs, e.g. sun."""
    unit: str
    """Unit of its levels, for logs, e.g. deg."""

    def read(self) -> Reading:
        """Current reading."""
        ...

    def listen(self, callback: Callable[[], object]) -> None:
        """Call `callback` whenever the level may have changed."""
        ...
