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

CI runs the checks, then the `deploy` job runs `scripts/deploy.sh` on a self-hosted
runner on the LAN. You can also run `scripts/deploy.sh [tag]` by hand from the Mac.

`deploy.sh` syncs `deploy/appdaemon/apps/` (shims + `apps.yaml`) to the add-on,
sets `python_packages` to the tag's tarball (other options preserved), and restarts
AppDaemon. Rollback: `scripts/deploy.sh v0.1.0`.

## One-time box setup

1. Install the **AppDaemon** and **Advanced SSH & Web Terminal** add-ons.
2. In the SSH add-on config, add your public key and set `sftp: true` (needed for rsync).
3. Create `.deploy.env` (gitignored):

       HA_SSH=root@homeassistant.local
       REPO_URL=https://github.com/<you>/ha-automations

## Self-hosted runner (Proxmox LXC)

1. Create an unprivileged Debian 12 LXC with 1 core, 512 MB RAM, and 4 GB disk.
2. Inside it:

       apt update && apt install -y git rsync python3 openssh-client curl
       useradd -m runner && su - runner
       ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519
       ssh-keyscan -p 22 <ha-ip> >> ~/.ssh/known_hosts

   Add `~/.ssh/id_ed25519.pub` to the SSH add-on's `authorized_keys`.
3. Repo → Settings → Actions → Runners → **New self-hosted runner** (Linux x64).
   Follow the download/config steps as `runner`, adding `--labels homelab` to
   `./config.sh`. Then, as root: `cd /home/runner/actions-runner && ./svc.sh install runner && ./svc.sh start`.
4. Repo → Settings → Environments → create `haos`. Set **Deployment branches and
   tags** to the tag pattern `v*`. Add the variable `HA_SSH=root@<ha-ip>`.
5. If the repo is public: Settings → Actions → General → set fork pull request
   workflows to require approval for all outside collaborators.

The SSH key stays on the runner. It is not stored in GitHub secrets.
