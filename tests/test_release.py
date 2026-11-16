import pytest

from ha_automations_release import (
    ReleaseError,
    config_repo,
    dev_version,
    latest_release,
    merge_release_pr,
    prior_dev_tags,
    prod_version,
    rebuild_docs,
    release_changelog,
    repo_from_url,
    unfinished_release,
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


def fake_release_commands(
    monkeypatch, fail_on: str | None = None, branch_on_origin: bool = True, log: str = ""
) -> list[str]:
    import ha_automations_release as rel

    calls: list[str] = []

    def run(*cmd: str, capture: bool = True) -> str:
        line = " ".join(cmd)
        calls.append(line)
        if fail_on and line.startswith(fail_on):
            raise ReleaseError(f"failed: {line}")
        if line.startswith("gh pr create"):
            return "https://github.com/you/ha-automations/pull/16"
        if line.startswith("gh pr view"):
            return "abc1234def"
        if line.startswith("git ls-remote --heads") and branch_on_origin:
            return "abc1234def\trefs/heads/release/v0.2.0"
        if line.startswith("git log"):
            return log
        return ""

    monkeypatch.setattr(rel, "run", run)
    monkeypatch.setattr(rel, "find_run", lambda *a, **k: {"databaseId": 1, "url": "ci"})
    monkeypatch.setattr(rel, "watch", lambda found, repo: calls.append(f"watch {found['url']}"))
    return calls


def test_merge_release_pr_merges_through_a_pull_request(monkeypatch):
    calls = fake_release_commands(monkeypatch)
    assert merge_release_pr("v0.2.0", "you/ha-automations") == "abc1234def"
    pr = "https://github.com/you/ha-automations/pull/16"
    assert calls == [
        "git switch -q -c release/v0.2.0",
        "git commit -q -m chore: release v0.2.0 -- CHANGELOG.md pyproject.toml uv.lock",
        "git push -q -u origin release/v0.2.0",
        (
            "gh pr create -R you/ha-automations --base main --head release/v0.2.0 "
            "--title chore: release v0.2.0 --body Release v0.2.0, opened by `uv run release prod`."
        ),
        "watch ci",
        f"gh pr merge {pr} -R you/ha-automations --squash --subject chore: release v0.2.0 --body ",
        f"gh pr view {pr} -R you/ha-automations --json mergeCommit -q .mergeCommit.oid",
        "git switch -q main",
        "git ls-remote --heads origin release/v0.2.0",
        "git push -q origin --delete release/v0.2.0",
        "git branch -q -D release/v0.2.0",
        "git pull -q --ff-only origin main",
    ]


def test_merge_release_pr_skips_a_branch_github_already_deleted(monkeypatch):
    calls = fake_release_commands(monkeypatch, branch_on_origin=False)
    merge_release_pr("v0.2.0", "you/ha-automations")
    assert not any("--delete" in c for c in calls)
    assert calls[-2:] == ["git branch -q -D release/v0.2.0", "git pull -q --ff-only origin main"]


def test_merge_release_pr_failure_names_the_open_pull_request(monkeypatch):
    calls = fake_release_commands(monkeypatch, fail_on="gh pr merge")
    with pytest.raises(ReleaseError, match=r"pull/16 is still open.*gh pr close"):
        merge_release_pr("v0.2.0", "you/ha-automations")
    assert calls[-1] == "git switch -q main"


LOG = """\
bbb ci: something after the release (#18)
aaa chore: release v0.2.0
999 feat: add a thing (#12)
888 chore: release v0.1.0
"""


def test_unfinished_release_finds_an_untagged_release_commit(monkeypatch):
    fake_release_commands(monkeypatch, log=LOG)
    assert unfinished_release({"v0.1.0", "v0.1.0.9001"}) == ("0.2.0", "aaa")


def test_unfinished_release_none_when_the_newest_release_is_tagged(monkeypatch):
    fake_release_commands(monkeypatch, log=LOG)
    assert unfinished_release({"v0.1.0", "v0.2.0"}) is None
    fake_release_commands(monkeypatch, log="999 feat: add a thing (#12)\n")
    assert unfinished_release(set()) is None


def test_unfinished_release_accepts_a_pull_request_number(monkeypatch):
    fake_release_commands(monkeypatch, log="aaa chore: release v0.3.0 (#20)\n")
    assert unfinished_release({"v0.2.0"}) == ("0.3.0", "aaa")


def test_rebuild_docs_starts_the_docs_workflow_on_main(monkeypatch):
    calls = fake_release_commands(monkeypatch)
    rebuild_docs("you/ha-automations")
    assert calls == ["gh workflow run docs.yml -R you/ha-automations --ref main"]
