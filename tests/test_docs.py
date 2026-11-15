import html
import json
import subprocess
from pathlib import Path

import pytest

import ha_automations_docs
from ha_automations_docs import (
    ASSET,
    download_release_docs,
    existing_tags,
    releases,
    set_version_map,
    upload_release_docs,
    version_map,
)


def test_releases_newest_first_without_dev_tags():
    tags = ["v0.1.0", "v0.1.0.9001", "v0.10.0", "v0.2.0", "v1.0", "other"]
    assert releases(tags) == ["0.10.0", "0.2.0", "0.1.0"]


def test_version_map_newest_release_is_latest_at_root():
    data = version_map(["0.2.0", "0.1.0"])
    assert data["versions"] == [
        {"tag": "dev", "label": "dev", "path_prefix": "v/dev", "prerelease": True},
        {"tag": "0.2.0", "label": "0.2.0", "latest": True, "path_prefix": ""},
        {"tag": "0.1.0", "label": "0.1.0", "path_prefix": "v/0.1.0"},
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
    git = fake_git(["v0.1.0", "v0.2.0", "v0.2.0.9001"], ["v0.1.0", "v0.3.0"])
    monkeypatch.setattr(ha_automations_docs, "git", git)
    assert existing_tags() == ["v0.1.0"]


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
