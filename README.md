# ha-automations

AppDaemon automations, developed and tested off-box. Releases go out as git tags,
and the AppDaemon add-on on HAOS pip-installs them. Nobody edits code on the box.

## Develop

    uv sync
    uv run pytest && uv run ruff check . && uv run pyright

To run against the real HA from your Mac, run `appdaemon` locally with a long-lived token.

## Release

1. Bump `version` in `pyproject.toml`, commit, then `git tag vX.Y.Z && git push --tags`.
2. In the AppDaemon add-on config, set `python_packages` to
   `git+https://github.com/<you>/ha-automations@vX.Y.Z` and restart the add-on.

## One-time box setup

Copy `deploy/appdaemon/apps/*` into the add-on's apps dir. The shims re-export
classes from the installed package, so they never need to change.
