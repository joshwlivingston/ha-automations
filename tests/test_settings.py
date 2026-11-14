from ha_automations.fades import LightFade
from ha_automations.settings import settings_for


def test_settings_for_keeps_only_init_fields():
    args = {"light": "light.x", "start": [], "off_level": 5, "from_level": 1, "ramp_from": 3}
    assert settings_for(LightFade, args, exclude=("light",)) == {"off_level": 5, "from_level": 1}
