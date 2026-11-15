import pytest

from ha_automations_release import (
    ReleaseError,
    dev_version,
    latest_release,
    prior_dev_tags,
    prod_version,
    release_changelog,
)

TAGS = {"v0.1.0", "v0.1.0.9001", "v0.1.0.9002", "v0.1.0.9003"}

CHANGELOG = """\
# Changelog

Intro.

## [Unreleased]

- New thing.

## [0.1.0] - 2026-11-14

- Initial release.

[Unreleased]: https://github.com/you/ha-automations/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/you/ha-automations/releases/tag/v0.1.0
"""


def test_dev_version_tags_current_version():
    assert dev_version("0.1.0.9004", TAGS) == "0.1.0.9004"


@pytest.mark.parametrize("current", ["0.1.0.9003", "0.1.0"])
def test_dev_version_refuses_tagged_or_release_version(current):
    with pytest.raises(ReleaseError):
        dev_version(current, TAGS)


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("patch", "0.1.1"), ("minor", "0.2.0"), ("major", "1.0.0"), ("0.3.0", "0.3.0"), ("v0.3.0", "0.3.0")],
)
def test_prod_version(bump, expected):
    assert prod_version("0.1.0.9003", bump, TAGS) == expected


@pytest.mark.parametrize("bump", ["0.1.0", "0.0.9", "huge"])
def test_prod_version_refuses(bump):
    with pytest.raises(ReleaseError):
        prod_version("0.1.0.9003", bump, TAGS)


def test_prior_dev_tags():
    tags = TAGS | {"v0.1.1", "v0.1.1.9001", "v0.0.9.9010"}
    assert prior_dev_tags(tags, "0.1.1") == ["v0.0.9.9010", "v0.1.0.9001", "v0.1.0.9002", "v0.1.0.9003"]


def test_latest_release():
    assert latest_release(TAGS | {"v0.10.0", "v0.9.0"}) == "v0.10.0"
    assert latest_release({"v0.1.0.9001"}) is None


def test_release_changelog():
    assert release_changelog(CHANGELOG, "0.1.1", "2026-11-15") == """\
# Changelog

Intro.

## [Unreleased]

## [0.1.1] - 2026-11-15

- New thing.

## [0.1.0] - 2026-11-14

- Initial release.

[Unreleased]: https://github.com/you/ha-automations/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/you/ha-automations/releases/tag/v0.1.1
[0.1.0]: https://github.com/you/ha-automations/releases/tag/v0.1.0
"""


def test_release_changelog_refuses_empty_unreleased():
    text = CHANGELOG.replace("- New thing.\n\n", "")
    with pytest.raises(ReleaseError, match="empty"):
        release_changelog(text, "0.1.1", "2026-11-15")
