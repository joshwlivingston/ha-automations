"""Detector protocol."""
from collections.abc import Callable
from typing import Protocol


class Detector(Protocol):
    def read(self) -> tuple[float | None, bool | None]:
        """(level, rising). level is None if unavailable; rising is None if unknown."""
        ...

    def listen(self, callback: Callable[[], object]) -> None:
        """Call `callback` whenever the level may have changed."""
        ...
