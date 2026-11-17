"""Runs great-docs with the Unreleased section of CHANGELOG.md first on the changelog page.

Great Docs builds the changelog from GitHub releases only. The docs command runs this for dev,
in its checkout, so dev docs show the changes that have not been released yet.

Usage:
    python -m ha_automations_docs.dev_build build --latest-only
"""

import re
import sys
from pathlib import Path

CHANGELOG = "CHANGELOG.md"
UNRELEASED = "## [Unreleased]"
LINK_REF = re.compile(r"^\[[^]]+\]: ")


def unreleased_notes(changelog: str) -> str:
    """Returns the body of the Unreleased section of changelog, empty if it has none."""
    lines: list[str] = []
    found = False
    for line in changelog.splitlines():
        if line.startswith("## ["):
            if found:
                break
            found = line.startswith(UNRELEASED)
        elif found and not LINK_REF.match(line):
            lines.append(line)
    return "\n".join(lines).strip()


def unreleased_release(notes: str, repo_url: str) -> dict[str, object]:
    """Returns a Great Docs release entry for the unreleased notes."""
    return {
        "tag_name": "Unreleased",
        "name": "Unreleased",
        "body": notes,
        "published_at": "",
        "html_url": f"{repo_url}/blob/main/{CHANGELOG}",
        "prerelease": False,
    }


def main() -> None:
    """Runs the great-docs command line with the Unreleased section added to the changelog."""
    # great-docs is in the docs group, which CI's checks do not install.
    from great_docs import cli  # pyright: ignore[reportMissingImports]
    from great_docs.core import GreatDocs  # pyright: ignore[reportMissingImports]

    notes = unreleased_notes(Path(CHANGELOG).read_text(encoding="utf-8"))
    fetch = GreatDocs._fetch_github_releases  # pyright: ignore[reportPrivateUsage]

    def fetch_with_unreleased(
        self: GreatDocs, owner: str, repo: str, max_releases: int = 50
    ) -> list[dict[str, object]]:
        releases = fetch(self, owner, repo, max_releases)
        if not notes:
            return releases
        url = f"https://github.com/{owner}/{repo}"
        return [unreleased_release(notes, url), *releases]

    GreatDocs._fetch_github_releases = fetch_with_unreleased  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
    sys.argv = ["great-docs", *sys.argv[1:]]
    cli.main()


if __name__ == "__main__":
    main()
