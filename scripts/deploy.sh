#!/usr/bin/env bash
# Deploy a tagged release to Home Assistant OS
#
# Release tags are vX.Y.Z. Dev tags are vX.Y.Z.9xxx and deploy only with DEV=1
#
# Steps:
#   1. Check the tag is a release tag (or a dev tag with DEV=1) and exists on REPO_URL
#   2. Skip if the HAOS box already runs this tag with this apps.yaml
#   3. Copy the shims in deploy/appdaemon/apps/ and your apps.yaml to the AppDaemon add-on
#   4. Set the add-on's python_packages to the tagged package. Other options are kept
#   5. Restart the add-on, unless NO_RESTART=1
#
# Requires the "Advanced SSH & Web Terminal" add-on with key auth
#
# Usage: scripts/deploy.sh [vX.Y.Z | vX.Y.Z.9xxx]
# The tag defaults to the version in pyproject.toml
#
# Settings, read from the environment or .deploy.env:
#   HA_SSH        ssh target, e.g. root@homeassistant.local (required)
#   APPS_YAML     path to your apps.yaml, absolute or relative to the repo root (required)
#   REPO_URL      package source, e.g. https://github.com/you/ha-automations (required)
#   HA_SSH_PORT   ssh port (default 22)
#   ADDON_SLUG    AppDaemon add-on slug (default a0d7b954_appdaemon)
#   APPS_DIR      apps directory on the HAOS box (default /addon_configs/$ADDON_SLUG/apps)
#   DEV           set to 1 to allow dev tags (vX.Y.Z.9xxx)
#   FORCE         set to 1 to deploy even if the HAOS box already runs this tag and apps.yaml
#   NO_RESTART    set to 1 to skip the add-on restart; the restart command is printed instead
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Settings ---

# Load .deploy.env if present
[[ -f .deploy.env ]] && source .deploy.env

# Stop if a required setting is missing
: "${HA_SSH:?set HA_SSH (e.g. root@homeassistant.local)}"
: "${APPS_YAML:?set APPS_YAML to the apps.yaml in your config repo}"
: "${REPO_URL:?set REPO_URL (e.g. https://github.com/you/ha-automations)}"

# Fill in defaults for optional settings
HA_SSH_PORT=${HA_SSH_PORT:-22}
ADDON_SLUG=${ADDON_SLUG:-a0d7b954_appdaemon}
APPS_DIR=${APPS_DIR:-/addon_configs/$ADDON_SLUG/apps}

# Tag to deploy. Defaults to the pyproject.toml version
version=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
tag=${1:-v$version}

# GitHub tarball location, so the HAOS box does not need git.
package="ha-automations@$REPO_URL/archive/refs/tags/$tag.tar.gz"

# --- Helpers ---

# Prints a message and exits with status 1
die() {
  echo "$1"
  exit 1
}

# Runs a command on the HAOS box over ssh
on_box() {
  ssh -p "$HA_SSH_PORT" "$HA_SSH" "$@"
}

# Prints the SHA-256 hash of stdin. Uses sha256sum, or shasum on macOS
sha256() {
  if command -v sha256sum >/dev/null; then
    sha256sum
  else
    shasum -a 256
  fi | cut -d' ' -f1
}

# Prints two lines: the deployed package, then the hash of the deployed apps.yaml
# Either is "none" if missing
deployed_state() {
  on_box bash -s -- "$ADDON_SLUG" "$APPS_DIR" <<'REMOTE'
curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" "http://supervisor/addons/$1/info" \
  | jq -r '[.data.options.python_packages // [] | .[] | select(startswith("ha-automations"))][0] // "none"'
{ sha256sum "$2/apps.yaml" 2>/dev/null || echo none; } | cut -d' ' -f1
REMOTE
}

# Replaces any ha-automations entry in python_packages with package
set_package() {
  on_box bash -s -- "$ADDON_SLUG" "$package" <<'REMOTE'
set -euo pipefail
slug=$1
package=$2
api=http://supervisor/addons/$slug
auth="Authorization: Bearer ${SUPERVISOR_TOKEN:?no SUPERVISOR_TOKEN in SSH session}"

opts=$(curl -fsS -H "$auth" "$api/info" | jq --arg s "$package" '
  .data.options
  | .python_packages = ([(.python_packages // [])[] | select(startswith("ha-automations") | not)] + [$s])')

curl -fsS -H "$auth" -H 'Content-Type: application/json' \
  -d "$(jq -n --argjson o "$opts" '{options: $o}')" "$api/options" >/dev/null
REMOTE
}

# Restarts the add-on
restart_addon() {
  on_box bash -s -- "$ADDON_SLUG" <<'REMOTE'
set -euo pipefail
curl -fsS -H "Authorization: Bearer ${SUPERVISOR_TOKEN:?no SUPERVISOR_TOKEN in SSH session}" \
  -X POST "http://supervisor/addons/$1/restart" >/dev/null
REMOTE
}

# --- 1. Check inputs ---

# Stop if apps.yaml is missing, so nothing is copied
[[ -f "$APPS_YAML" ]] || die "APPS_YAML not found: $APPS_YAML"

# Stop unless the tag is a release tag, or a dev tag with DEV=1
if [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  :
elif [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+\.9[0-9]{3}$ ]]; then
  [[ "${DEV:-}" == 1 ]] || die "$tag is a dev tag. Set DEV=1 to deploy it."
else
  die "$tag is not a release tag (vX.Y.Z) or dev tag (vX.Y.Z.9xxx)."
fi

# Stop if the tag is not on REPO_URL. pip on the HAOS box downloads the tag's tarball, so it
# would fail after the files were already copied
git ls-remote --exit-code --tags "$REPO_URL" "refs/tags/$tag" >/dev/null \
  || die "tag $tag not found on $REPO_URL. Push it first."

# --- 2. Skip if already deployed ---

# Ask the HAOS box what it runs. If the package and apps.yaml both match, exit
# FORCE=1 skips this check
if [[ "${FORCE:-}" != 1 ]]; then
  { read -r current_package; read -r current_sha; } < <(deployed_state)
  if [[ "$current_package" == "$package" && "$current_sha" == "$(sha256 < "$APPS_YAML")" ]]; then
    echo "Already running $tag with this apps.yaml. Set FORCE=1 to redeploy."
    exit 0
  fi
  echo "Currently deployed: $current_package"
fi

# --- 3. Copy files ---

# Replace the shims and apps.yaml on the HAOS box
echo "Syncing apps to $HA_SSH:$APPS_DIR"
rsync -az --delete --exclude '__pycache__' --exclude 'apps.yaml' \
  -e "ssh -p $HA_SSH_PORT" deploy/appdaemon/apps/ "$HA_SSH:$APPS_DIR/"
rsync -az -e "ssh -p $HA_SSH_PORT" "$APPS_YAML" "$HA_SSH:$APPS_DIR/apps.yaml"

# --- 4. Set package ---

# Set the package version. It installs when the add-on next starts
echo "Setting python_packages to [$package]"
set_package

# --- 5. Restart ---

# Restart the add-on so it installs the package and loads apps.yaml
# NO_RESTART=1 skips the restart and prints the command to run it later
if [[ "${NO_RESTART:-}" == 1 ]]; then
  echo "Deployed $tag without restarting. To restart: ssh -p $HA_SSH_PORT $HA_SSH ha addons restart $ADDON_SLUG"
else
  echo "Restarting $ADDON_SLUG"
  restart_addon
  echo "Deployed $tag."
fi

# Print the command to view add-on logs
echo "Logs: ssh -p $HA_SSH_PORT $HA_SSH ha addons logs $ADDON_SLUG"
