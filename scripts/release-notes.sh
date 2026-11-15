#!/usr/bin/env bash
# Print the CHANGELOG.md section for a version
#
# Usage: scripts/release-notes.sh vX.Y.Z
set -euo pipefail
cd "$(dirname "$0")/.."

version=${1:?usage: scripts/release-notes.sh vX.Y.Z}
version=${version#v}

notes=$(awk -v v="$version" '
  /^## \[/ { found = index($0, "## [" v "]") == 1; next }
  /^\[[^]]+\]: / { next }
  found
' CHANGELOG.md | sed '/./,$!d')

[[ -n "$notes" ]] || { echo "no CHANGELOG.md section for $version" >&2; exit 1; }
echo "$notes"
