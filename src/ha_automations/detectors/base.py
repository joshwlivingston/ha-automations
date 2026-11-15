"""Detector protocol and the reading it returns."""
from collections.abc import Callable
from typing import NamedTuple, Protocol


class Reading(NamedTuple):
    """A detector's level and direction. level is None if unavailable; rising is None if unknown."""

    level: float | None
    rising: bool | None


class Detector(Protocol):
    def read(self) -> Reading:
        """Current reading."""
        ...

    def listen(self, callback: Callable[[], object]) -> None:
        """Call `callback` whenever the level may have changed."""
        ...
