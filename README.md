# ha-automations

Home Assistant automations written in Python and run by the AppDaemon add-on. Changes are tested in CI and deployed to Home Assistant OS from a tagged release.

**Docs: https://joshwlivingston.github.io/ha-automations/**

## Apps

### Lights

- [Sunrise Fade](https://joshwlivingston.github.io/ha-automations/docs/apps/sunrise-fade.html): turns a light on dim before dawn and brightens it as the sun rises.
- [Sunset Fade](https://joshwlivingston.github.io/ha-automations/docs/apps/sunset-fade.html): brightens a light as the sun sets.
- [Light Fade](https://joshwlivingston.github.io/ha-automations/docs/apps/light-fade.html): the general fade. Choose your own levels and triggers.

```yaml
bedroom_sunrise:
  module: sunrise_fade
  class: SunriseFade
  light: light.bedroom_lamp
```

## Get started

Your settings go in a separate private config repo. Start from the template: **[ha-automations-config-template](https://github.com/joshwlivingston/ha-automations-config-template)**. Its README walks through setup. Then follow the [Get Started guide](https://joshwlivingston.github.io/ha-automations/user-guide/overview.html).

## Fork it

Fork this repo to add or change apps. Point your config repo at your fork instead of this one by setting its `PACKAGE_REPO` variable.

## Issues and pull requests

Bug reports, ideas, and pull requests are welcome. Before opening a PR, run:

```sh
uv run pytest && uv run ruff check . && uv run pyright
```
