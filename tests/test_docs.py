import html
import json
import subprocess
from pathlib import Path

import pytest

import ha_automations_docs
from ha_automations_docs import (
    ASSET,
    DEV,
    DEV_BUILD,
    Output,
    apply_working_changes,
    download_release_docs,
    existing_tags,
    fit,
    great_docs,
    set_version_map,
    upload_release_docs,
    version_map,
    versions_of,
    working_changes,
    working_hash,
)
from ha_automations_docs.dev_build import unreleased_notes


def test_versions_of_releases_and_dev_tags_newest_first():
    tags = [
        "v0.1.0",
        "v0.1.0.9001",
        "v0.1.0.9002",
        "v0.10.0",
        "v0.2.0",
        "v1.0",
        "v0.1.0.1",
        "x",
    ]
    assert versions_of(tags) == ["0.10.0", "0.2.0", "0.1.0.9002", "0.1.0.9001", "0.1.0"]


def test_version_map_newest_release_is_latest_at_root():
    data = version_map(["0.2.0", "0.1.0"])
    assert data["versions"] == [
        {"tag": "dev", "label": "dev", "path_prefix": "v/dev", "prerelease": True},
        {"tag": "0.2.0", "label": "0.2.0", "latest": True, "path_prefix": ""},
        {"tag": "0.1.0", "label": "0.1.0", "path_prefix": "v/0.1.0"},
    ]


def test_version_map_dev_tags_are_prereleases_below_dev():
    data = version_map(["0.1.0.9002", "0.1.0.9001", "0.1.0"])
    assert data["versions"] == [
        {"tag": "dev", "label": "dev", "path_prefix": "v/dev", "prerelease": True},
        {
            "tag": "0.1.0.9002",
            "label": "0.1.0.9002",
            "path_prefix": "v/0.1.0.9002",
            "prerelease": True,
        },
        {
            "tag": "0.1.0.9001",
            "label": "0.1.0.9001",
            "path_prefix": "v/0.1.0.9001",
            "prerelease": True,
        },
        {"tag": "0.1.0", "label": "0.1.0", "latest": True, "path_prefix": ""},
    ]


def test_set_version_map_replaces_meta_content():
    page = '<head><meta name="gd-version-map" content="{&quot;old&quot;:1}"></head>'
    data = version_map(["0.1.0"])
    new = set_version_map(page, data)
    content = new.split('content="')[1].split('"')[0]
    assert json.loads(html.unescape(content)) == data
    assert new.startswith("<head>") and new.endswith("</head>")


def fake_git(local: list[str], remote: list[str] | None):
    def git(*args: str) -> str:
        if args[0] == "tag":
            return "\n".join(local)
        if remote is None:
            raise subprocess.CalledProcessError(128, "git")
        return "\n".join(f"abc123\trefs/tags/{t}" for t in remote)

    return git


def test_existing_tags_skips_tags_deleted_on_origin(monkeypatch: pytest.MonkeyPatch):
    git = fake_git(
        ["v0.1.0", "v0.1.0.9001", "v0.2.0"], ["v0.1.0", "v0.1.0.9001", "v0.3.0"]
    )
    monkeypatch.setattr(ha_automations_docs, "git", git)
    assert existing_tags() == ["v0.1.0", "v0.1.0.9001"]


def test_existing_tags_uses_local_tags_without_origin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ha_automations_docs, "git", fake_git(["v0.1.0"], None))
    assert existing_tags() == ["v0.1.0"]


def test_release_docs_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    stored = tmp_path / "stored.tar.gz"
    calls: list[list[str]] = []

    def gh(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[2] == "upload":
            stored.write_bytes(Path(cmd[4]).read_bytes())
        elif stored.exists():
            (Path(cmd[cmd.index("--dir") + 1]) / ASSET).write_bytes(stored.read_bytes())
        else:
            return subprocess.CompletedProcess(cmd, 1, "", "release not found")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(ha_automations_docs.subprocess, "run", gh)
    site = tmp_path / "site"
    (site / "docs").mkdir(parents=True)
    (site / "index.html").write_text("home")
    (site / "docs" / "page.html").write_text("page")

    dest = tmp_path / "archive" / "0.1.0"
    dest.parent.mkdir()
    assert not download_release_docs("0.1.0", dest)
    upload_release_docs("0.1.0", site)
    assert download_release_docs("0.1.0", dest)
    assert (dest / "index.html").read_text() == "home"
    assert (dest / "docs" / "page.html").read_text() == "page"
    assert calls[1][:4] == ["gh", "release", "upload", "v0.1.0"]


def test_working_changes_are_applied_to_a_checkout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)

    def sh(*cmd: str) -> None:
        subprocess.run(cmd, check=True, capture_output=True)

    sh("git", "init", "-q")
    Path(".gitignore").write_text("ignored.txt\n")
    for name in ("kept.qmd", "edited.qmd", "staged.qmd", "deleted.qmd", "moved.qmd"):
        Path(name).write_text("old")
    sh("git", "add", ".")
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    tree = tmp_path / "tree"
    sh("git", "worktree", "add", "-q", "--detach", str(tree))

    Path("edited.qmd").write_text("new")
    Path("staged.qmd").write_text("new")
    sh("git", "add", "staged.qmd")
    Path("deleted.qmd").unlink()
    sh("git", "mv", "moved.qmd", "renamed.qmd")
    Path("docs").mkdir()
    Path("docs/untracked.qmd").write_text("new")
    Path("ignored.txt").write_text("new")
    before = working_hash()

    assert working_changes() == [
        "deleted.qmd",
        "docs/untracked.qmd",
        "edited.qmd",
        "moved.qmd",
        "renamed.qmd",
        "staged.qmd",
    ]
    apply_working_changes("dev", tree)
    assert sorted(p.name for p in tree.rglob("*.qmd")) == [
        "edited.qmd",
        "kept.qmd",
        "renamed.qmd",
        "staged.qmd",
        "untracked.qmd",
    ]
    assert (tree / "edited.qmd").read_text() == "new"
    assert (tree / "staged.qmd").read_text() == "new"
    assert not (tree / "ignored.txt").exists()

    Path("edited.qmd").write_text("newer")
    assert working_hash() != before


def test_parallel_output_prints_each_log_as_one_block(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    out = Output()
    out.start(["dev", "0.1.0"])
    out.line("dev", "-- Step  1/19 - Prepare")
    out.line("0.1.0", "uv output")
    out.line("dev", "dev detail")
    out.line("0.1.0", "-- Step  1/19 - Prepare")
    out.done("0.1.0", "Built")
    out.done("dev", "Built")
    assert capsys.readouterr().out.splitlines() == [
        "[dev] -- Step  1/19 - Prepare",
        "[0.1.0] -- Step  1/19 - Prepare",
        "===== 0.1.0 =====",
        "[0.1.0] uv output",
        "[0.1.0] -- Step  1/19 - Prepare",
        "[0.1.0] Built",
        "===== dev =====",
        "[dev] -- Step  1/19 - Prepare",
        "[dev] dev detail",
        "[dev] Built",
    ]


def test_single_build_output_streams(capsys: pytest.CaptureFixture[str]):
    out = Output()
    out.start(["dev"])
    out.line("dev", "detail")
    out.done("dev", "Built")
    assert capsys.readouterr().out.splitlines() == ["[dev] detail", "[dev] Built"]


def test_fit_counts_wide_characters_as_two_columns():
    assert fit("ab🎉cd", 4) == "ab🎉"
    assert fit("ab🎉cd", 3) == "ab"
    assert fit("abc", 10) == "abc"


@pytest.mark.parametrize("tag", ["v0.1.0.9001", "v1.0", "main"])
def test_attach_refuses_non_release_tags(tag: str):
    with pytest.raises(ha_automations_docs.DocsError, match="not a release tag"):
        ha_automations_docs.attach(
            ha_automations_docs.parser().parse_args(["attach", tag])
        )


def test_unreleased_notes_reads_only_the_unreleased_section():
    changelog = (
        "# Changelog\n\nIntro.\n\n## [Unreleased]\n\n### Bugfixes\n\n- Fix (#2).\n\n"
        "## [0.1.0] - 2026-01-01\n\n- Old (#1).\n\n[0.1.0]: https://example.com\n"
    )
    assert unreleased_notes(changelog) == "### Bugfixes\n\n- Fix (#2)."


def test_unreleased_notes_empty_without_the_section():
    assert unreleased_notes("# Changelog\n\n## [0.1.0]\n\n- Old.\n") == ""
    assert unreleased_notes("## [Unreleased]\n\n## [0.1.0]\n\n- Old.\n") == ""


def test_dev_runs_dev_build_when_the_checkout_has_it(tmp_path: Path):
    assert great_docs(DEV, tmp_path)[0] == "great-docs"
    (tmp_path / DEV_BUILD).parent.mkdir(parents=True)
    (tmp_path / DEV_BUILD).touch()
    assert great_docs(DEV, tmp_path)[:3] == [
        "python",
        "-m",
        "ha_automations_docs.dev_build",
    ]
    assert great_docs("0.1.0", tmp_path)[0] == "great-docs"
