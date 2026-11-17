# Contributing

## Checks

```sh
uv run pytest && uv run ruff check . && uv run pyright
```

CI runs these on every push and pull request.

## Scope

ha-automations decides what to do to entities and when. Home Assistant config defines the entities and how devices report and accept values.

| ha-automations | Home Assistant config |
|---|---|
| Logic that changes over time (fades, ramps, curves) | Entities (template lights, helpers, groups) |
| Decisions that depend on state (sun position, light levels, start triggers) | Fixes to how a device reports or accepts values (calibration, scaling, inverting) |
| Logic that needs tests, logs and docs | Integrations, devices, areas, dashboards |
| Reusable apps, configured per instance in `apps.yaml` | One-off glue a YAML automation handles |

A stateless conversion between values goes in Home Assistant config. Logic with state, timing or decisions goes here.

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

Default arguments are subject to change. A change to a default is a patch release.

```sh
uv run release dev                              # tag the current dev version and deploy it
uv run release prod [patch|minor|major|X.Y.Z]   # release vX.Y.Z, default patch
```

Both run the checks, push the tag, wait for CI, then run the config repo's deploy workflow and wait for it. `prod` first moves `## [Unreleased]` in `CHANGELOG.md` to the new version and bumps it, commits that to a `release/vX.Y.Z` branch, opens a pull request, waits for its CI, squash-merges it and tags the merge commit (`main` only accepts pull requests). It deletes older dev tags once CI and the deploy succeed. If a run stops after merging the release pull request, run `uv run release prod` again to tag and deploy that release. If it stops early, run `uv run release prune-dev-tags`.

| Option | Meaning |
|---|---|
| `--dry-run` | Show what would happen, change nothing |
| `--no-deploy` | Push the tag, skip the deploy workflow |
| `--force` | Redeploy even if the box runs this tag |
| `-y` | Do not ask for confirmation |

The deploy workflow runs in `CONFIG_REPO` (environment or `.deploy.env`), default `<origin owner>/ha-automations-config`.

## Docs

```sh
uv run docs preview   # serve the site at http://127.0.0.1:8000/, building it first if needed
uv run docs build     # build the site into great-docs/_site
```

Needs [Quarto](https://quarto.org). Pages are for users: no internals. Settings tables, defaults and charts come from the code through `docs/_helpers.py`.

The site has a version selector:

| Version | Built from | Path |
|---|---|---|
| `dev` | the working tree, uncommitted and untracked files included (`--ref` for a ref) | `v/dev/` |
| dev tags (`vX.Y.Z.9NNN`) | the tag | `v/X.Y.Z.9NNN/` |
| releases (`vX.Y.Z`) | the tag | `v/X.Y.Z/`, and the newest at the root |

- Each tag builds once and is reused after that: locally from `.docs-archive/`, in CI from `docs-site.tar.gz` on its GitHub release (releases) or the Actions cache (dev tags). `--rebuild` builds every tag again; in CI, delete a release's `docs-site.tar.gz` to rebuild it.
- Only tags that also exist on `origin` build. Docs for deleted tags are dropped.
- Versions that need building build in parallel (`--jobs`). A terminal shows one live status line per build; each build's full log prints as one block when it finishes (a collapsible group in GitHub Actions).
- `preview` skips the build when the site matches the working tree, the tags and the docs tool; `--build` builds anyway.
- CI's `release` job attaches a release's docs right after publishing it (`uv run docs attach vX.Y.Z`). The docs workflow runs `uv run docs build --ref HEAD --release-assets` and deploys to GitHub Pages on each push to `main`, when CI passes on a new tag, and when a tag is deleted; it also attaches docs to any release still missing them. GitHub sends no event when more than three tags are deleted at once, so `uv run release` starts the docs workflow itself after deleting dev tags. After deleting tags by hand, run `gh workflow run docs.yml`.

## Commits

One-line conventional commits. `feat` and `fix` PRs add a user-facing line under `## [Unreleased]` in `CHANGELOG.md`. `args` PRs add a row to the `### Defaults` table there instead (App, Setting, Was, Now).

| Type | For | Release |
|---|---|---|
| `args` | A change to a default argument | patch |
