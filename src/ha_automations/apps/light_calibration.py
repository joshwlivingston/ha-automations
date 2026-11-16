"""Register a calibration for a light. Every app controlling that light uses it.

With `slider` set, an input_number helper (0 to 100, step 1) controls the light
through the calibration: 0 is off, 1 to 100 is calibrated brightness. The slider
follows the light when anything else changes it.

Usage
-----
bedroom_lamp_calibration:
    module: light_calibration
    class: LightCalibrationApp
    light: light.bedroom_lamp
    slider: input_number.bedroom_lamp
    calibration:
      kind: linear
      low: 27
      high: 205

Settings
--------
Each field of LightCalibrationSettings has a description. Unknown settings are an error.
"""
import appdaemon.plugins.hass.hassapi as hass
from pydantic import Field

from ha_automations.calibrations import CalibrationConfig, register, unregister
from ha_automations.config import APPDAEMON_KEYS, Config
from ha_automations.lights import HassLight
from ha_automations.logs import line


class LightCalibrationSettings(Config):
    light: str = Field(description="Light to calibrate, e.g. `light.bedroom_lamp`")
    calibration: CalibrationConfig = Field(
        description="How percent maps to the bulb's raw brightness, e.g. `{kind: linear, low: 27, high: 205}`"
    )
    slider: str | None = Field(
        None,
        description="input_number helper (0 to 100, step 1) that controls the light through the calibration. 0 is off. Unset means no slider",
    )


class LightCalibrationApp(hass.Hass):
    def initialize(self):
        args = {k: v for k, v in self.args.items() if k not in APPDAEMON_KEYS}
        s = self.settings = LightCalibrationSettings.model_validate(args)
        register(s.light, s.calibration)
        self.light = HassLight(self, s.light, s.calibration)
        self._pushed: int | None = None
        if s.slider is not None:
            self.listen_state(self._on_slider, s.slider)
            self.listen_state(self._on_light, s.light)
            self.listen_state(self._on_light, s.light, attribute="brightness")
            self._on_light()
        slider = f" slider={s.slider}" if s.slider else ""
        self.log(line("load", "init", f"light={s.light} calibration={s.calibration.label}{slider}"))

    def terminate(self):
        unregister(self.settings.light)

    def _slider_pct(self) -> int | None:
        try:
            return round(float(str(self.get_state(self.settings.slider))))
        except (TypeError, ValueError):
            return None

    def _on_slider(self, *args, **kwargs):
        """Set the light from the slider, unless the change came from _on_light."""
        pct = self._slider_pct()
        if pct is None or pct == self._pushed:
            return
        self._pushed = None
        if pct == self.light.brightness_pct():
            return
        if pct <= 0:
            self.light.turn_off(0)
        else:
            self.light.turn_on(pct, 0)

    def _on_light(self, *args, **kwargs):
        """Move the slider to the light's calibrated brightness."""
        pct = self.light.brightness_pct()
        if pct == self._slider_pct():
            return
        self._pushed = pct
        self.call_service("input_number/set_value", entity_id=self.settings.slider, value=pct)
