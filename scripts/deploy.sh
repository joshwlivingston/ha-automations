#!/usr/bin/env bash
# Deploy a tagged release to HAOS in one step:
#   1. sync deploy/appdaemon/apps/ shims + your apps.yaml (from your config repo)
#      into the AppDaemon add-on
#   2. set the add-on's python_packages to the tagged package (other options preserved)
#   3. restart the add-on
#
# Requires the "Advanced SSH & Web Terminal" add-on with key auth.
#
# Usage: scripts/deploy.sh [vX.Y.Z]   (defaults to the version in pyproject.toml)
#
# Config (env or .deploy.env):
#   HA_SSH         ssh target, e.g. root@homeassistant.local   (required)
#   HA_SSH_PORT    default 22
#   APPS_YAML      path to your apps.yaml, relative to this repo root or absolute (required)
#   REPO_URL       package source, e.g. https://github.com/you/ha-automations (required)
#   ADDON_SLUG     default a0d7b954_appdaemon
#   APPS_DIR       default /addon_configs/$ADDON_SLUG/apps
#   FORCE          set to 1 to deploy even if the box already runs this tag + apps.yaml
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -f .deploy.env ]] && source .deploy.env
: "${HA_SSH:?set HA_SSH (e.g. root@homeassistant.local)}"
: "${APPS_YAML:?set APPS_YAML to your config repo apps.yaml}"
[[ -f "$APPS_YAML" ]] || { echo "APPS_YAML not found: $APPS_YAML"; exit 1; }
REPO_URL=${REPO_URL:?set REPO_URL (e.g. https://github.com/you/ha-automations)}
HA_SSH_PORT=${HA_SSH_PORT:-22}
ADDON_SLUG=${ADDON_SLUG:-a0d7b954_appdaemon}
APPS_DIR=${APPS_DIR:-/addon_configs/$ADDON_SLUG/apps}

version=$(python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
tag=${1:-v$version}

# Refuse to deploy a tag GitHub doesn't have — pip would fail on the box.
git ls-remote --exit-code --tags "$REPO_URL" "refs/tags/$tag" >/dev/null \
  || { echo "tag $tag not found on $REPO_URL — push it first"; exit 1; }

# Tarball URL: no git needed inside the add-on container.
spec="ha-automations @ $REPO_URL/archive/refs/tags/$tag.tar.gz"
ssh_cmd=(ssh -p "$HA_SSH_PORT" "$HA_SSH")

sha256() { if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi | cut -d' ' -f1; }

# Skip if the box already runs this tag (which fixes the shims) with this apps.yaml.
if [[ "${FORCE:-}" != 1 ]]; then
  {
    read -r current_spec
    read -r current_sha
  } < <("${ssh_cmd[@]}" bash -s -- "$ADDON_SLUG" "$APPS_DIR" <<'REMOTE'
curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" "http://supervisor/addons/$1/info" \
  | jq -r '[.data.options.python_packages // [] | .[] | select(startswith("ha-automations"))][0] // "none"'
{ sha256sum "$2/apps.yaml" 2>/dev/null || echo none; } | cut -d' ' -f1
REMOTE
  )
  if [[ "$current_spec" == "$spec" && "$current_sha" == "$(sha256 < "$APPS_YAML")" ]]; then
    echo "✓ already running $tag with this apps.yaml (FORCE=1 to redeploy)"; exit 0
  fi
  echo "deployed: $current_spec"
fi

echo "→ syncing apps to $HA_SSH:$APPS_DIR"
# --delete removes shims for apps you've deleted; keep add-on-generated files.
rsync -az --delete --exclude '__pycache__' --exclude 'apps.yaml' \
  -e "ssh -p $HA_SSH_PORT" deploy/appdaemon/apps/ "$HA_SSH:$APPS_DIR/"
rsync -az -e "ssh -p $HA_SSH_PORT" "$APPS_YAML" "$HA_SSH:$APPS_DIR/apps.yaml"

echo "→ setting python_packages = [$spec] and restarting $ADDON_SLUG"
"${ssh_cmd[@]}" bash -s -- "$ADDON_SLUG" "$spec" <<'REMOTE'
set -euo pipefail
slug=$1 spec=$2
api=http://supervisor/addons/$slug
auth="Authorization: Bearer ${SUPERVISOR_TOKEN:?no SUPERVISOR_TOKEN in SSH session}"
# Replace only our package; keep any other packages and options.
opts=$(curl -fsS -H "$auth" "$api/info" | jq --arg s "$spec" '
  .data.options
  | .python_packages = ([(.python_packages // [])[] | select(startswith("ha-automations") | not)] + [$s])')
curl -fsS -H "$auth" -H 'Content-Type: application/json' \
  -d "$(jq -n --argjson o "$opts" '{options: $o}')" "$api/options" >/dev/null
curl -fsS -H "$auth" -X POST "$api/restart" >/dev/null
REMOTE

echo "✓ deployed $tag — tail logs: ssh -p $HA_SSH_PORT $HA_SSH ha addons logs $ADDON_SLUG"
