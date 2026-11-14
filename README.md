# ha-automations

AppDaemon automations, developed and tested off-box. Releases go out as git tags,
and the AppDaemon add-on on HAOS pip-installs them. Nobody edits code on the box.

## Develop

    uv sync
    uv run pytest && uv run ruff check . && uv run pyright

To run against the real HA from your Mac, run `appdaemon` locally with a long-lived token.

## Release + deploy

    # bump version in pyproject.toml, commit, then:
    git tag vX.Y.Z && git push && git push --tags
    scripts/deploy.sh

`deploy.sh` syncs `deploy/appdaemon/apps/` (shims + `apps.yaml`) to the add-on,
sets `python_packages` to the tag's tarball (other options preserved), and restarts
AppDaemon. Rollback: `scripts/deploy.sh v0.1.0`.

## One-time box setup

1. Install the **AppDaemon** and **Advanced SSH & Web Terminal** add-ons.
2. In the SSH add-on config, add your public key and set `sftp: true` (needed for rsync).
3. Create `.deploy.env` (gitignored):

       HA_SSH=root@homeassistant.local
       REPO_URL=https://github.com/<you>/ha-automations

