import pytest
from pydantic import TypeAdapter, ValidationError

from ha_automations.calibrations import (
    Calibration,
    CalibrationConfig,
    FullRange,
    Linear,
)

LINEAR = Linear(low=27, high=205)
ALL = [FullRange(), LINEAR, Linear(low=1, high=100)]


def test_calibration_is_abstract():
    with pytest.raises(TypeError):
        Calibration()  # type: ignore[abstract]


@pytest.mark.parametrize("cal", ALL, ids=lambda c: c.label)
def test_round_trips(cal):
    assert all(cal.to_pct(cal.to_raw(p)) == p for p in range(1, 101))


@pytest.mark.parametrize("cal", ALL, ids=lambda c: c.label)
def test_raw_in_range(cal):
    assert all(1 <= cal.to_raw(p) <= 255 for p in range(1, 101))


def test_full_range_ends():
    assert FullRange().to_raw(100) == 255
    assert FullRange().to_raw(1) == 3


def test_linear_ends_and_clamps():
    assert (LINEAR.to_raw(1), LINEAR.to_raw(100)) == (27, 205)
    assert (LINEAR.to_pct(10), LINEAR.to_pct(255)) == (1, 100)


def test_linear_needs_high_above_low():
    with pytest.raises(ValidationError):
        Linear(low=200, high=100)


def test_config_picks_kind():
    adapter = TypeAdapter(CalibrationConfig)
    assert adapter.validate_python({"kind": "linear", "low": 27, "high": 205}) == LINEAR
    assert adapter.validate_python({"kind": "full_range"}) == FullRange()
    with pytest.raises(ValidationError):
        adapter.validate_python({"low": 27, "high": 205})


def test_registry():
    from ha_automations.calibrations import calibration_for, register, unregister

    assert calibration_for("light.x") == FullRange()
    register("light.x", LINEAR)
    assert calibration_for("light.x") == LINEAR
    unregister("light.x")
    assert calibration_for("light.x") == FullRange()
