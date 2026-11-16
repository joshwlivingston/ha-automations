# ha-automations

Automations for Home Assistant, configured in one file. Runs on the AppDaemon add-on.

**Docs: https://joshwlivingston.github.io/ha-automations/**

## Apps

### Lights

- [Sunrise Fade](https://joshwlivingston.github.io/ha-automations/docs/apps/sunrise-fade.html): turns a light on dim before dawn and brightens it as the sun rises.
- [Sunset Fade](https://joshwlivingston.github.io/ha-automations/docs/apps/sunset-fade.html): brightens a light as the sun sets.
- [Light Fade](https://joshwlivingston.github.io/ha-automations/docs/apps/light-fade.html): a fade with your own levels, start times and direction.
- [Light Calibration](https://joshwlivingston.github.io/ha-automations/docs/apps/light-calibration.html): makes 1% the dimmest a bulb glows and 100% its full brightness, with an optional dashboard slider.

```yaml
bedroom_sunrise:
  module: sunrise_fade
  class: SunriseFade
  light: light.bedroom_lamp
```

## Get started

Follow the [Get started guide](https://joshwlivingston.github.io/ha-automations/user-guide/overview.html). Your settings go in a private config repo made from [ha-automations-config-template](https://github.com/joshwlivingston/ha-automations-config-template).

## Contributing

Bug reports, ideas and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) to fork, add apps and release.
