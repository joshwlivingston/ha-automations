"""Uncalibrated: percent spread over the whole raw range."""
from typing import Literal

from pydantic import Field

from ha_automations.calibrations.base import MAX_RAW, Calibration, clamp_pct


class FullRange(Calibration):
    """1 to 100 percent over 1 to MAX_RAW raw, as Home Assistant's brightness_pct does."""

    kind: Literal["full_range"] = Field(default="full_range", description="Calibration kind")

    def to_raw(self, pct: int) -> int:
        return max(round(clamp_pct(pct) * MAX_RAW / 100), 1)

    def to_pct(self, raw: int) -> int:
        return clamp_pct(raw * 100 / MAX_RAW)

    @property
    def label(self) -> str:
        return "full_range"
