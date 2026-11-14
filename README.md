# ha-automations

Home Assistant automations written in Python and run by the AppDaemon add-on. Changes are tested in CI and deployed to Home Assistant OS from a tagged release.

## You need your own config repo

This repo holds the code only. Your settings (which lights, what times, your Home Assistant address) go in a separate private repo that you own.

Start from the template: **[ha-automations-config-template](#)** *(coming soon)*.

## Quickstart

You need:

- Home Assistant OS
- The [**AppDaemon**](https://community.home-assistant.io/t/home-assistant-community-add-on-appdaemon-4/163259) add-on
- The [**Advanced SSH & Web Terminal**](https://community.home-assistant.io/t/home-assistant-community-add-on-ssh-web-terminal/33820) add-on, set up with an SSH key

Steps:

1. Create your config repo from the template above.
2. In your config repo, edit `apps.yaml` to point at your lights. Example:

   ```yaml
   bedroom_rising_light:
     module: rising_light_fade
     class: RisingLightFade
     light: light.bedroom_lamp
   ```

3. Fill in your Home Assistant SSH address in the config repo's settings.
4. Deploy using the steps in the config repo.
5. Check the AppDaemon add-on log in Home Assistant to confirm the apps started.

Each app's settings are listed at the top of its file in `src/ha_automations/apps/`.

## Fork it

Fork this repo if you want to add or change automations. Point your config repo at your fork instead of this one.

## Issues and pull requests

Bug reports, ideas, and pull requests are welcome. Before opening a PR, run:

```sh
uv run pytest && uv run ruff check . && uv run pyright
```
