# Contributing

## Checks

```sh
uv run pytest && uv run ruff check . && uv run pyright
```

CI runs these on every push and pull request.

## Layout

| Path | Holds |
|---|---|
| `src/ha_automations/apps/` | AppDaemon apps and their settings models |
| `src/ha_automations/fades.py`, `curves.py` | Fade logic and math, no Home Assistant imports |
| `src/ha_automations/detectors/` | Light level sources |
| `src/ha_automations/triggers.py` | Start triggers |
| `src/ha_automations/lights.py` | Light control |
| `deploy/appdaemon/apps/` | One-line shims AppDaemon loads; no logic |
| `scripts/deploy.sh` | Deploys a tag to Home Assistant OS |
| `docs/`, `index.qmd`, `great-docs.yml` | The docs site |

## Fork

1. Fork this repo.
2. Point your config repo at the fork. The deploy workflow installs from `<config repo owner>/ha-automations`, so a fork under the same account needs nothing. Otherwise set the `PACKAGE_REPO` variable. For `scripts/deploy.sh`, set `REPO_URL`.
3. Release from the fork. Deploys install its tags.

## Add an app

1. Add `src/ha_automations/apps/<name>.py`: a `Config` subclass for its settings, every field with a `Field(description=...)`, and an AppDaemon app class that validates its args with it. Keep logic that does not need Home Assistant in its own module, tested with fakes. See `light_fade.py` and `fades.py`.
2. Add the shim `deploy/appdaemon/apps/<name>.py`, importing the app class.
3. Add tests under `tests/`.
4. Add `docs/apps/<name>.qmd` following the existing app pages. Render settings with `docs/_helpers.py`. Add the app to `docs/apps/index.qmd`, the homepage, the module table in `docs/user_guide/10-apps-yaml.qmd`, and the README. A new group of apps gets its own section in `docs/apps/index.qmd` and a `sidebar_groups` entry in `great-docs.yml`. Keep User Guide pages app-agnostic; topics shared by one group go in `docs/apps/`.

A light fade with other defaults: subclass `LightFadeSettings` for the defaults and `LightFadeApp` with `Settings` set to it. See `sunset_fade.py`. Add it to the parametrized tests in `tests/test_apps.py`.

## Add a detector

1. Add `src/ha_automations/detectors/<name>.py`: a class with `read()` and `listen()`, and a `Config` model with `kind: Literal["<name>"]` and a `build(app)` method. See `sun.py`.
2. Make `DetectorConfig` in `detectors/__init__.py` a union discriminated on `kind`.

## Add a trigger

1. Add a `Config` model with a `listen(app, callback)` method to `triggers.py`.
2. Add it to the `TriggerConfig` union.
3. Add it to the triggers tables in `docs/apps/light-fade.qmd` and `docs/apps/start-triggers.qmd`.

## Versions and releases

Every change bumps the dev version, for example `uv version 0.1.0.9004`.

```sh
uv run release dev                              # tag the current dev version and deploy it
uv run release prod [patch|minor|major|X.Y.Z]   # release vX.Y.Z, default patch
```

Both run the checks, push the tag, wait for CI, then run the config repo's deploy workflow and wait for it. `prod` also moves `## [Unreleased]` in `CHANGELOG.md` to the new version, commits, and deletes older dev tags once CI and the deploy succeed. If it stops early, run `uv run release prune-dev-tags`.

| Option | Meaning |
|---|---|
| `--dry-run` | Show what would happen, change nothing |
| `--no-deploy` | Push the tag, skip the deploy workflow |
| `--force` | Redeploy even if the box runs this tag |
| `-y` | Do not ask for confirmation |

The deploy workflow runs in `CONFIG_REPO` (environment or `.deploy.env`), default `<origin owner>/ha-automations-config`.

## Docs

```sh
uv sync --group docs
uv run great-docs preview
```

Needs [Quarto](https://quarto.org). Pages are for users: no internals. Settings tables, defaults and charts come from the code through `docs/_helpers.py`.

The site has a version selector. The newest release is the root, each release is under `v/X.Y.Z/`, and `main` is under `v/dev/`. Each push to `main` runs `scripts/build_docs.py`, which builds `main` and any release tag (`vX.Y.Z`) not yet in the `docs-archive` branch, then deploys to GitHub Pages. A release builds once from its own tag and is reused from `docs-archive` after that. To rebuild a release, delete its directory from `docs-archive`.

To build the versioned site locally (releases are cached in `.docs-archive/`):

```sh
uv run --no-project scripts/build_docs.py
python3 -m http.server -d great-docs/_site
```

## Commits

One-line conventional commits. `feat` and `fix` PRs add a user-facing line under `## [Unreleased]` in `CHANGELOG.md`.
