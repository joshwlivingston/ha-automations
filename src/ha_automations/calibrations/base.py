"""Calibration base class."""
from abc import ABC, abstractmethod

from ha_automations.config import Config

MAX_RAW = 255


class Calibration(Config, ABC):
    """Maps percent brightness (1 to 100) to and from a light's raw brightness (1 to MAX_RAW).

    Off (0 percent, 0 raw) is not mapped. Subclasses implement the two conversions
    and should round trip every percent: to_pct(to_raw(p)) == p.
    """

    @abstractmethod
    def to_raw(self, pct: int) -> int:
        """Raw brightness for a percent from 1 to 100."""

    @abstractmethod
    def to_pct(self, raw: int) -> int:
        """Percent from 1 to 100 for a raw brightness from 1 to MAX_RAW."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Short description for logs."""


def clamp_pct(pct: float) -> int:
    return min(max(round(pct), 1), 100)
