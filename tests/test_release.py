import pytest

from ha_automations_release import (
    ReleaseError,
    config_repo,
    dev_version,
    latest_release,
    prior_dev_tags,
    prod_version,
    release_changelog,
    repo_from_url,
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


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/fork-owner/ha-automations.git",
        "https://github.com/fork-owner/ha-automations",
        "git@github.com:fork-owner/ha-automations.git",
        "ssh://git@github.com/fork-owner/ha-automations.git",
    ],
)
def test_repo_from_url(url):
    assert repo_from_url(url) == "fork-owner/ha-automations"


def test_repo_from_url_refuses_non_github():
    with pytest.raises(ReleaseError):
        repo_from_url("https://gitlab.com/you/ha-automations.git")


def test_config_repo_uses_origin_owner(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CONFIG_REPO", raising=False)
    assert config_repo("fork-owner/ha-automations") == "fork-owner/ha-automations-config"
    monkeypatch.setenv("CONFIG_REPO", "someone/config")
    assert config_repo("fork-owner/ha-automations") == "someone/config"
