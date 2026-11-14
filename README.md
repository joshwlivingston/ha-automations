# ha-automations

AppDaemon automations, developed and tested off-box. Releases go out as git tags,
and the AppDaemon add-on on HAOS pip-installs them. Nobody edits code on the box.

## Develop

    uv sync
    uv run pytest && uv run ruff check . && uv run pyright

To run against the real HA from your Mac, run `appdaemon` locally with a long-lived token.

## Layout: public code, private config

This repo holds generic code only. Your entity IDs live in a separate **private
config repo** that contains `apps.yaml` and a workflow. On a schedule, the workflow
resolves the latest `v*` tag of `PACKAGE_REPO`, checks out that tag, and runs
`scripts/deploy.sh` with `APPS_YAML` pointing at its own `apps.yaml`.

`PACKAGE_REPO` defaults to `<config repo owner>/ha-automations`. A fork under the
same name needs no edits, only the `HA_SSH` variable. `deploy.sh` exits after one
SSH call if the box already runs that tag with the same `apps.yaml`; `FORCE=1`
redeploys anyway.

## Release

    # bump version in pyproject.toml, commit, then:
    git tag vX.Y.Z && git push && git push --tags

CI here only runs checks. Your config repo checks for new tags every 15 minutes
and deploys the latest one. It also redeploys when you push config changes. No
tokens connect the two repos.

## Deploy

`scripts/deploy.sh [tag]` syncs the shims in `deploy/appdaemon/apps/` and your
`apps.yaml` to the add-on. It then sets `python_packages` to the tag's tarball
(other options preserved) and restarts AppDaemon.

To run it by hand from your machine, create `.deploy.env` (gitignored):

    HA_SSH=root@homeassistant.local
    REPO_URL=https://github.com/<you>/ha-automations
    APPS_YAML=../ha-automations-config/apps.yaml

## One-time box setup

1. Install the **AppDaemon** and **Advanced SSH & Web Terminal** add-ons.
2. In the SSH add-on config, add your public key and set `sftp: true` (needed for rsync).

## Self-hosted runner (Proxmox LXC)

1. Create an unprivileged Debian 12 LXC with 1 core, 512 MB RAM, and 4 GB disk.
2. Inside it:

       apt update && apt install -y git rsync python3 openssh-client curl
       useradd -m runner && su - runner
       ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519
       ssh-keyscan -p 22 <ha-ip> >> ~/.ssh/known_hosts

   Add `~/.ssh/id_ed25519.pub` to the SSH add-on's `authorized_keys`.
3. **Config repo** → Settings → Actions → Runners → **New self-hosted runner** (Linux x64).
   Follow the download/config steps as `runner`, adding `--labels homelab` to
   `./config.sh`. Then, as root: `cd /home/runner/actions-runner && ./svc.sh install runner && ./svc.sh start`.
4. **Config repo** → Settings → Environments → create `haos`. Set **Deployment branches** to `main`. Add the variable `HA_SSH=root@<ha-ip>`.
The SSH key stays on the runner. The runner is registered only on your private config repo,
so the public repo never runs jobs on your LAN. The key is not stored in GitHub secrets.
