"""Tag a dev or prod release of ha-automations and deploy it from the config repo.

Usage:
    uv run release dev                              tag the current vX.Y.Z.9NNN version
    uv run release prod [patch|minor|major|X.Y.Z]   release vX.Y.Z (default patch)
    uv run release prune-dev-tags                   delete dev tags older than the latest release

dev and prod run the checks, push the tag, wait for CI, then run the config repo's deploy
workflow and wait for it. prod also updates CHANGELOG.md and the version, commits, and deletes
dev tags older than the release once everything succeeded.

Settings, read from the environment or .deploy.env:
    CONFIG_REPO   config repo running the deploy workflow (default <owner>/ha-automations-config)

All GitHub calls use the origin remote's repo, so a fork deploys from the fork.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RELEASE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
DEV = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)\.(9\d{3})$")
CHANGELOG = "CHANGELOG.md"
VERSION_FILES = ["CHANGELOG.md", "pyproject.toml", "uv.lock"]
DEPLOY_WORKFLOW = "deploy.yml"
CI_WORKFLOW = "ci.yml"
POLL_SECONDS = 5
POLL_TRIES = 24
GITHUB_URL = re.compile(r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$")


class ReleaseError(Exception):
    """A check failed; the message says why."""


# --- Versions ---


def base(version: str) -> tuple[int, int, int]:
    """Returns the X.Y.Z part of a release or dev version."""
    m = RELEASE.match(version) or DEV.match(version)
    if not m:
        raise ReleaseError(f"{version} is not X.Y.Z or X.Y.Z.9NNN")
    return int(m[1]), int(m[2]), int(m[3])


def dev_version(current: str, tags: set[str]) -> str:
    """Returns the dev version to tag: the current version, if it is a dev version not yet tagged."""
    if not DEV.match(current):
        raise ReleaseError(f"version {current} is not a dev version (X.Y.Z.9NNN). Bump it first.")
    if f"v{current}" in tags:
        raise ReleaseError(
            f"v{current} is already tagged. The change since then should have bumped the version."
        )
    return current


def prod_version(current: str, bump: str, tags: set[str]) -> str:
    """Returns the release version for bump (patch, minor, major or X.Y.Z) from current."""
    x, y, z = base(current)
    if bump == "patch":
        new = f"{x}.{y}.{z + 1}"
    elif bump == "minor":
        new = f"{x}.{y + 1}.0"
    elif bump == "major":
        new = f"{x + 1}.0.0"
    elif RELEASE.match(bump):
        new = bump.removeprefix("v")
    else:
        raise ReleaseError(f"bump must be patch, minor, major or X.Y.Z, not {bump}")
    if f"v{new}" in tags:
        raise ReleaseError(f"v{new} is already tagged")
    releases = [base(t) for t in tags if RELEASE.match(t)]
    if releases and base(new) <= max(releases):
        latest = "v{}.{}.{}".format(*max(releases))
        raise ReleaseError(f"v{new} is not later than the latest release {latest}")
    return new


def prior_dev_tags(tags: set[str], version: str) -> list[str]:
    """Returns the dev tags whose X.Y.Z is older than version, oldest first."""
    found = [t for t in tags if DEV.match(t) and base(t) < base(version)]
    return sorted(found, key=lambda t: (base(t), t.rsplit(".", 1)[1]))


def latest_release(tags: set[str]) -> str | None:
    """Returns the latest vX.Y.Z tag, or None."""
    releases = [t for t in tags if RELEASE.match(t)]
    return max(releases, key=base) if releases else None


def repo_from_url(url: str) -> str:
    """Returns owner/name from a GitHub remote URL."""
    if m := GITHUB_URL.search(url):
        return m["repo"]
    raise ReleaseError(f"origin {url} is not a GitHub repo")


# --- Changelog ---


def release_changelog(text: str, version: str, date: str) -> str:
    """Moves the Unreleased section of CHANGELOG.md to a section for version and updates the links."""
    heading = "## [Unreleased]"
    lines = text.splitlines()
    try:
        start = lines.index(heading)
    except ValueError:
        raise ReleaseError(f"no '{heading}' line in {CHANGELOG}") from None
    end = start + 1
    while end < len(lines) and not lines[end].startswith("## ") and not re.match(r"^\[[^]]+\]: ", lines[end]):
        end += 1
    if not any(line.strip() for line in lines[start + 1 : end]):
        raise ReleaseError(f"the Unreleased section of {CHANGELOG} is empty")

    link = re.compile(r"^\[Unreleased\]: (?P<repo>.+)/compare/v[^.]\S*\.\.\.HEAD$")
    for i, line in enumerate(lines):
        if m := link.match(line):
            repo = m["repo"]
            lines[i : i + 1] = [
                f"[Unreleased]: {repo}/compare/v{version}...HEAD",
                f"[{version}]: {repo}/releases/tag/v{version}",
            ]
            break
    else:
        raise ReleaseError(f"no '[Unreleased]: <repo>/compare/vX.Y.Z...HEAD' link in {CHANGELOG}")

    lines[start : start + 1] = [heading, "", f"## [{version}] - {date}"]
    return "\n".join(lines) + "\n"


# --- Commands ---


def run(*cmd: str, capture: bool = True) -> str:
    """Runs cmd and returns its stdout. Raises ReleaseError if it fails."""
    result = subprocess.run(cmd, check=False, text=True, capture_output=capture)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        raise ReleaseError(f"failed: {' '.join(cmd)}" + (f"\n{detail}" if detail else ""))
    return (result.stdout or "").strip() if capture else ""


def all_tags() -> set[str]:
    """Returns the v* tags on origin and in the local repo."""
    remote = run("git", "ls-remote", "--tags", "--refs", "origin", "v*")
    tags = {line.split("refs/tags/", 1)[1] for line in remote.splitlines() if "refs/tags/" in line}
    return tags | set(run("git", "tag", "-l", "v*").split())


def setting(name: str) -> str | None:
    """Returns a setting from the environment or .deploy.env."""
    if value := os.environ.get(name):
        return value
    env = Path(".deploy.env")
    if env.is_file():
        for line in env.read_text().splitlines():
            if m := re.match(rf"^\s*(?:export\s+)?{name}=(.*)$", line):
                return m[1].strip().strip("'\"")
    return None


def origin_repo() -> str:
    """Returns owner/name of the origin remote."""
    return repo_from_url(run("git", "remote", "get-url", "origin"))


def config_repo(origin: str) -> str:
    """Returns the config repo, from CONFIG_REPO or <origin owner>/ha-automations-config."""
    if repo := setting("CONFIG_REPO"):
        return repo
    return f"{origin.split('/')[0]}/ha-automations-config"


def preflight(dry_run: bool) -> None:
    """Checks the repo is clean and in sync with origin/main, then runs the checks."""
    if run("git", "status", "--porcelain"):
        raise ReleaseError("working tree is not clean")
    run("gh", "auth", "status")
    run("git", "fetch", "--tags", "origin")
    problems = []
    if (branch := run("git", "branch", "--show-current")) != "main":
        problems.append(f"on branch {branch}, not main")
    elif run("git", "rev-parse", "HEAD") != run("git", "rev-parse", "origin/main"):
        problems.append("main is not the same as origin/main")
    if problems and not dry_run:
        raise ReleaseError("; ".join(problems))
    for problem in problems:
        print(f"Dry run, ignoring: {problem}")
    print("Running checks")
    run("uv", "run", "pytest", "-q", capture=False)
    run("uv", "run", "ruff", "check", ".", capture=False)
    run("uv", "run", "pyright", capture=False)


def confirm(question: str, yes: bool) -> bool:
    """Asks a yes/no question. Returns True without asking if yes is set."""
    if yes:
        return True
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def find_run(repo: str, workflow: str, *filters: str, since: str | None = None) -> dict:
    """Polls repo for the newest run of workflow matching filters, created at or after since."""
    cmd = ["gh", "run", "list", "-R", repo, "--workflow", workflow, "--json", "databaseId,url,createdAt", "-L", "5"]
    cmd += list(filters)
    for _ in range(POLL_TRIES):
        runs = [r for r in json.loads(run(*cmd)) if since is None or r["createdAt"] >= since]
        if runs:
            return runs[0]
        time.sleep(POLL_SECONDS)
    raise ReleaseError(f"no {workflow} run found on {repo}")


def watch(found: dict, repo: str) -> None:
    """Waits for a workflow run on repo and raises ReleaseError if it fails."""
    print(f"Watching {found['url']}")
    run(
        "gh", "run", "watch", str(found["databaseId"]), "-R", repo,
        "--exit-status", "--interval", str(POLL_SECONDS),
        capture=False,
    )


def delete_tags(tags: list[str]) -> None:
    """Deletes tags on origin and locally."""
    remote = set(run("git", "ls-remote", "--tags", "--refs", "origin", "v*").split())
    if on_origin := [t for t in tags if f"refs/tags/{t}" in remote]:
        run("git", "push", "origin", "--delete", *on_origin)
    local = set(run("git", "tag", "-l", "v*").split())
    if here := [t for t in tags if t in local]:
        run("git", "tag", "-d", *here)
    print(f"Deleted {', '.join(tags)}")


def release(kind: str, args: argparse.Namespace) -> None:
    """Runs a dev or prod release."""
    preflight(args.dry_run)
    tags = all_tags()
    current = run("uv", "version", "--short")
    version = dev_version(current, tags) if kind == "dev" else prod_version(current, args.bump, tags)
    tag = f"v{version}"
    stale = prior_dev_tags(tags, version) if kind == "prod" else []
    origin = origin_repo()
    repo = None if args.no_deploy else config_repo(origin)

    edited = False
    try:
        if kind == "prod":
            edited = True
            run("uv", "version", version, "--no-sync")
            changelog = Path(CHANGELOG)
            today = datetime.date.today().isoformat()
            changelog.write_text(release_changelog(changelog.read_text(), version, today))
            run("scripts/release-notes.sh", tag)
            print(run("git", "diff", "--", CHANGELOG))
            print(run("git", "diff", "--stat"))

        print(f"Tag: {tag} ({kind}) on {origin}")
        if repo:
            print(f"Deploy: {DEPLOY_WORKFLOW} on {repo} with version={tag} dev={kind == 'dev'} force={args.force}")
        if stale:
            print(f"Dev tags to delete after success: {', '.join(stale)}")

        if args.dry_run:
            print("Dry run, reverting and stopping before commit, tag and push")
            return
        if not confirm("Push and deploy?", args.yes):
            print("Stopped")
            return

        if kind == "prod":
            run("git", "commit", "-q", "-m", f"chore: release {tag}", "--", *VERSION_FILES)
        run("git", "tag", tag)
        edited = False
    finally:
        if edited:
            run("git", "checkout", "--", *VERSION_FILES)

    refs = ["main", tag] if kind == "prod" else [tag]
    run("git", "push", "--atomic", "origin", *refs)
    print(f"Pushed {' and '.join(refs)}")

    watch(find_run(origin, CI_WORKFLOW, "--branch", tag), origin)

    if repo:
        since = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        run(
            "gh", "workflow", "run", DEPLOY_WORKFLOW, "-R", repo,
            "-f", f"version={tag}",
            "-f", f"dev={'true' if kind == 'dev' else 'false'}",
            "-f", f"force={'true' if args.force else 'false'}",
        )
        watch(find_run(repo, DEPLOY_WORKFLOW, "--event", "workflow_dispatch", since=since), repo)

    if stale:
        delete_tags(stale)
    print(f"Released {tag}")


def prune(args: argparse.Namespace) -> None:
    """Deletes dev tags older than the latest release."""
    run("git", "fetch", "--tags", "origin")
    tags = all_tags()
    latest = latest_release(tags)
    if latest is None:
        raise ReleaseError("no release tags")
    stale = prior_dev_tags(tags, latest)
    if not stale:
        print(f"No dev tags older than {latest}")
        return
    print(f"Dev tags older than {latest}: {', '.join(stale)}")
    if args.dry_run or not confirm("Delete them?", args.yes):
        return
    delete_tags(stale)


def parser() -> argparse.ArgumentParser:
    """Builds the command line parser."""
    p = argparse.ArgumentParser(prog="release", description="Release ha-automations and deploy it.")
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    common.add_argument("--dry-run", action="store_true", help="show what would happen and change nothing")

    deploy = argparse.ArgumentParser(add_help=False, parents=[common])
    deploy.add_argument("--no-deploy", action="store_true", help="push the tag but do not deploy")
    deploy.add_argument("--force", action="store_true", help="redeploy even if the box runs this tag")

    sub.add_parser("dev", parents=[deploy], help="tag the current dev version and deploy it")
    prod = sub.add_parser("prod", parents=[deploy], help="release vX.Y.Z and deploy it")
    prod.add_argument("bump", nargs="?", default="patch", help="patch (default), minor, major or X.Y.Z")
    sub.add_parser("prune-dev-tags", parents=[common], help="delete dev tags older than the latest release")
    return p


def main() -> None:
    """Runs the release command."""
    args = parser().parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # pyright: ignore[reportAttributeAccessIssue]
    os.chdir(run("git", "rev-parse", "--show-toplevel"))
    try:
        if args.command == "prune-dev-tags":
            prune(args)
        else:
            release(args.command, args)
    except ReleaseError as e:
        sys.exit(f"release: {e}")
    except KeyboardInterrupt:
        sys.exit("release: interrupted")
