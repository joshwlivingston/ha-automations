"""Linear calibration between a measured low and high raw brightness."""
from typing import Literal, Self

from pydantic import Field, model_validator

from ha_automations.calibrations.base import MAX_RAW, Calibration, clamp_pct


class Linear(Calibration):
    """1 percent is low, 100 percent is high, evenly spaced between."""

    kind: Literal["linear"] = Field(default="linear", description="Calibration kind")
    low: int = Field(ge=1, le=MAX_RAW, description="Lowest raw brightness (1 to 255) the light reliably turns on at. Used for 1%")
    high: int = Field(ge=1, le=MAX_RAW, description="Raw brightness (1 to 255) above which the light gets no brighter. Used for 100%")

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.high <= self.low:
            raise ValueError("high must be above low")
        return self

    def to_raw(self, pct: int) -> int:
        return round(self.low + (clamp_pct(pct) - 1) * (self.high - self.low) / 99)

    def to_pct(self, raw: int) -> int:
        return clamp_pct(1 + (raw - self.low) * 99 / (self.high - self.low))

    @property
    def label(self) -> str:
        return f"linear {self.low}..{self.high}"
