"""Build and preview the ha-automations docs site with a version selector.

Usage:
    uv run docs build     build the site into great-docs/_site
    uv run docs preview   serve the site, building it first unless it is up to date

Versions are dev, release tags (vX.Y.Z) and dev tags (vX.Y.Z.9NNN). dev is the working tree,
uncommitted and untracked files included, or --ref. Only tags that also exist on origin build.
Each tag builds once from its own checkout and is kept in the archive directory as ARCHIVE/X.Y.Z/;
a build builds dev and any tag whose docs are missing (all of them with --rebuild), and drops
archived docs for tags that no longer exist. With --release-assets, release docs come from, and
new ones go to, docs-site.tar.gz on their GitHub release instead of the archive; CI uses this.
Builds run in parallel; see Output for how their logs show. The site puts the
newest release at the root, every tag under v/<version>/ and dev under v/dev/. The version list
baked into each page is rewritten so every page lists every version.
"""

import argparse
import contextlib
import fcntl
import functools
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unicodedata
import webbrowser
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# vX.Y.Z for a release, vX.Y.Z.9NNN for a dev tag.
VERSION_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)(?:\.(9\d{3}))?")
VERSION_META = re.compile(r'<meta name="gd-version-map" content="[^"]*">')
DEV = "dev"
ARCHIVE = ".docs-archive"
OUT = "great-docs/_site"
# Release asset holding a release's built docs.
ASSET = "docs-site.tar.gz"
# Worktree add and remove edit shared files in .git, so they run one at a time.
GIT_LOCK = threading.Lock()
# Build output that only applies to a full Great Docs versioned site.
DROP = ["v", "_redirects", "vercel.json", "_version_map.json"]


class DocsError(Exception):
    """A build failed; the message says why."""


def git(*args: str) -> str:
    """Runs git and returns its output."""
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def versions_of(tags: list[str]) -> list[str]:
    """Returns the versions among tags, releases and dev tags, newest first."""
    found = [m for t in tags if (m := VERSION_TAG.fullmatch(t))]
    found.sort(key=lambda m: tuple(int(g) for g in m.groups() if g), reverse=True)
    return [m.group(0)[1:] for m in found]


def is_release(version: str) -> bool:
    """Returns whether version is a release (X.Y.Z) rather than a dev tag (X.Y.Z.9NNN)."""
    return version.count(".") == 2


def existing_tags() -> list[str]:
    """Returns local tags that also exist on origin, so tags deleted on origin are not built.

    Without origin (offline, no remote) it warns and returns all local tags.
    """
    local = git("tag", "--list", "v*").split()
    try:
        lines = git("ls-remote", "--tags", "--refs", "origin", "v*").splitlines()
    except subprocess.CalledProcessError:
        print("Warning: could not list tags on origin, using local tags")
        return local
    remote = {line.split("refs/tags/", 1)[1] for line in lines if "refs/tags/" in line}
    for tag in versions_of(local):
        if f"v{tag}" not in remote:
            print(
                f"Skipping v{tag}: deleted on origin (git fetch --prune --prune-tags)"
            )
    for tag in versions_of(sorted(remote - set(local))):
        print(f"Skipping v{tag}: on origin but not here (git fetch --tags)")
    return [t for t in local if t in remote]


def version_map(versions: list[str]) -> dict[str, object]:
    """Returns the selector's version map: dev, then tags newest first.

    The newest release is latest, at the root. Dev tags are prereleases.
    """
    latest = next((v for v in versions if is_release(v)), None)
    entries: list[dict[str, object]] = [
        {"tag": DEV, "label": DEV, "path_prefix": f"v/{DEV}", "prerelease": True}
    ]
    for version in versions:
        entry: dict[str, object] = {"tag": version, "label": version}
        if version == latest:
            entry |= {"latest": True, "path_prefix": ""}
        else:
            entry["path_prefix"] = f"v/{version}"
        if not is_release(version):
            entry["prerelease"] = True
        entries.append(entry)
    return {"versions": entries, "pages": {}}


def set_version_map(page: str, data: dict[str, object]) -> str:
    """Returns page with its version map meta tag set to data."""
    content = html.escape(json.dumps(data, separators=(",", ":")))
    meta = f'<meta name="gd-version-map" content="{content}">'
    return VERSION_META.sub(lambda _: meta, page)


class Output:
    """Shows the output of version builds.

    One build streams its lines. Several builds keep each build's lines together: a terminal shows
    one live status line per build, other output shows each build's step lines, and each build's
    full log prints as one block when it finishes, in a collapsible group on GitHub Actions.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.stream = True
        self.tty = sys.stdout.isatty()
        self.github = os.environ.get("GITHUB_ACTIONS") == "true"
        self.logs: dict[str, list[str]] = {}
        self.status: dict[str, str] = {}
        self.drawn = 0
        self.last_draw = 0.0

    def start(self, tags: list[str]) -> None:
        """Starts showing builds of tags."""
        self.stream = len(tags) == 1
        self.logs = {t: [] for t in tags}
        self.status = dict.fromkeys(tags, "waiting")
        self.drawn = 0

    def line(self, tag: str, text: str) -> None:
        """Shows a line of output from the build of tag."""
        with self.lock:
            if self.stream or tag not in self.logs:
                print(f"[{tag}] {text}")
                return
            self.logs[tag].append(text)
            if text.strip():
                self.status[tag] = text.strip()
            if self.tty:
                self.draw()
            elif text.lstrip().startswith("-- Step"):
                print(f"[{tag}] {text.strip()}")

    def done(self, tag: str, summary: str) -> None:
        """Shows that the build of tag finished, with its full log when builds run in parallel."""
        with self.lock:
            if self.stream or tag not in self.logs:
                print(f"[{tag}] {summary}")
                return
            self.clear()
            print(f"::group::{tag}: {summary}" if self.github else f"===== {tag} =====")
            for text in self.logs.pop(tag):
                print(f"[{tag}] {text}")
            if self.github:
                print("::endgroup::")
            print(f"[{tag}] {summary}")
            del self.status[tag]
            if self.tty:
                self.draw(force=True)

    def clear(self) -> None:
        """Erases the status lines."""
        if self.drawn:
            sys.stdout.write(f"\x1b[{self.drawn}F\x1b[J")
            self.drawn = 0

    def draw(self, force: bool = False) -> None:
        """Redraws the status lines, at most ten times a second unless forced."""
        now = time.monotonic()
        if not force and now - self.last_draw < 0.1:
            return
        self.last_draw = now
        self.clear()
        width = shutil.get_terminal_size().columns - 1
        for tag, text in self.status.items():
            print(fit(f"[{tag}] {text}", width))
        self.drawn = len(self.status)
        sys.stdout.flush()


OUTPUT = Output()


def fit(text: str, width: int) -> str:
    """Returns text cut to fit width terminal columns, counting wide characters as two."""
    used = 0
    for i, char in enumerate(text):
        used += 2 if unicodedata.east_asian_width(char) in "WF" else 1
        if used > width:
            return text[:i]
    return text


def say(tag: str, line: str) -> None:
    """Shows a line about the build of tag."""
    OUTPUT.line(tag, line)


def run(tag: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
    """Runs cmd, passing its output through prefixed with tag."""
    say(tag, "$ " + " ".join(cmd))
    with subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            say(tag, line.rstrip())
    if proc.returncode:
        raise DocsError(f"{tag}: {cmd[0]} exited with {proc.returncode}")


def working_changes() -> list[str]:
    """Returns files that differ from HEAD in the working tree: changed, deleted and untracked."""
    changed = git("diff", "-z", "--name-only", "--no-renames", "HEAD")
    untracked = git("ls-files", "-z", "--others", "--exclude-standard")
    return sorted({p for p in (changed + untracked).split("\0") if p})


def working_hash() -> str:
    """Returns a hash of the working tree changes from working_changes."""
    digest = hashlib.sha256()
    for name in working_changes():
        path = Path(name)
        digest.update(name.encode() + b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"\0deleted\0")
    return digest.hexdigest()


def apply_working_changes(tag: str, tree: Path) -> None:
    """Copies the working tree changes into tree, a checkout of HEAD."""
    changes = working_changes()
    for name in changes:
        src, dest = Path(name), tree / name
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        elif dest.is_file():
            dest.unlink()
    say(
        tag,
        f"Applied {len(changes)} uncommitted file(s): {', '.join(changes) or 'none'}",
    )


def build_version(
    ref: str, tag: str, tags: list[str], dest: Path, working: bool = False
) -> None:
    """Builds the docs at ref as version tag into dest, with the working tree changes if working."""
    start = time.monotonic()
    # Listing every version makes Great Docs add the selector; tag is latest so it builds at the root.
    versions = [{"tag": t, "label": t, "latest": t == tag} for t in tags]
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    try:
        build_checkout(ref, tag, versions, dest, working, env)
    except Exception as e:
        OUTPUT.done(tag, f"Failed: {e}")
        raise
    OUTPUT.done(tag, f"Built from {ref} in {time.monotonic() - start:.0f}s")


def build_checkout(
    ref: str,
    tag: str,
    versions: list[dict[str, object]],
    dest: Path,
    working: bool,
    env: dict[str, str],
) -> None:
    """Builds the docs in a checkout of ref with the versions list, and copies the site to dest."""
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tree"
        say(tag, f"Checking out {ref} in {tree}")
        with GIT_LOCK:
            git("worktree", "add", "--quiet", "--detach", str(tree), ref)
        try:
            if working:
                apply_working_changes(tag, tree)
            with open(tree / "great-docs.yml", "a") as f:
                f.write(f"\nversions: {json.dumps(versions)}\n")
            run(tag, ["uv", "sync", "--locked", "--group", "docs"], tree, env)
            run(
                tag,
                ["uv", "run", "--no-sync", "great-docs", "build", "--latest-only"],
                tree,
                env,
            )
            site = tree / "great-docs" / "_site"
            for name in DROP:
                path = site / name
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            say(tag, f"Copying the site to {dest}")
            replace_dir(site, dest)
        finally:
            with GIT_LOCK:
                git("worktree", "remove", "--force", str(tree))


def replace_dir(src: Path, dest: Path) -> None:
    """Copies src to dest, replacing it. Copies then renames, so a failure never leaves a partial dest."""
    partial = dest.with_name(dest.name + ".partial")
    for path in (partial, dest):
        if path.exists():
            shutil.rmtree(path)
    shutil.copytree(src, partial)
    partial.rename(dest)


def download_release_docs(version: str, dest: Path) -> bool:
    """Downloads the docs attached to release vVERSION into dest. Returns False if there are none."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [
                "gh",
                "release",
                "download",
                f"v{version}",
                "--pattern",
                ASSET,
                "--dir",
                tmp,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            print(f"No {ASSET} on release v{version}, building it")
            return False
        site = Path(tmp) / "site"
        site.mkdir()
        with tarfile.open(Path(tmp) / ASSET) as tar:
            tar.extractall(site, filter="data")
        replace_dir(site, dest)
    print(f"Downloaded {ASSET} from release v{version}")
    return True


def upload_release_docs(version: str, site: Path) -> None:
    """Attaches site to release vVERSION as ASSET, replacing any earlier one."""
    with tempfile.TemporaryDirectory() as tmp:
        asset = Path(tmp) / ASSET
        with tarfile.open(asset, "w:gz") as tar:
            tar.add(site, arcname=".")
        result = subprocess.run(
            ["gh", "release", "upload", f"v{version}", str(asset), "--clobber"],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode:
        print(
            f"Warning: could not attach {ASSET} to release v{version}, the next build tries again: "
            + result.stderr.strip()
        )
    else:
        print(f"Attached {ASSET} to release v{version}")


def stamp(ref: str | None, versions: list[str]) -> dict[str, object]:
    """Returns what a site build depends on: the dev commit and changes, the versions and this tool."""
    return {
        "dev": git("rev-parse", f"{ref or 'HEAD'}^{{commit}}").strip(),
        "changes": working_hash() if ref is None else None,
        "versions": versions,
        "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def stamp_path(out: Path) -> Path:
    """Returns where the stamp of the site in out is kept."""
    return out.with_name(out.name + ".build.json")


@contextlib.contextmanager
def build_lock(out: Path) -> Iterator[None]:
    """Holds a lock next to out, so two builds never write the same site at once."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out.with_name(out.name + ".lock"), "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DocsError(f"another docs build is writing {out}") from None
        yield


def build(args: argparse.Namespace, versions: list[str] | None = None) -> Path:
    """Builds the site and returns its directory."""
    with build_lock(args.out.resolve()):
        return build_unlocked(args, versions)


def build_unlocked(args: argparse.Namespace, versions: list[str] | None) -> Path:
    """Builds the site and returns its directory, without taking the lock."""
    archive: Path = args.archive.resolve()
    out: Path = args.out.resolve()
    if versions is None:
        versions = versions_of(existing_tags())
    tags = [DEV, *versions]
    print(f"Versions: {', '.join(tags)}")
    # Taken before building, so edits made during the build make the next preview build again.
    built = stamp(args.ref, versions)

    archive.mkdir(parents=True, exist_ok=True)
    # Drop archived docs for tags that no longer exist and leftovers from failed copies.
    for path in archive.iterdir():
        if (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in versions
        ):
            print(f"Removing {path}: no tag v{path.name}")
            shutil.rmtree(path)
    stamp_path(out).unlink(missing_ok=True)
    if out.exists():
        shutil.rmtree(out)

    builds = [(args.ref or "HEAD", DEV, out / "v" / DEV, args.ref is None)]
    for v in versions:
        dest = archive / v
        if args.rebuild:
            builds.append((f"v{v}", v, dest, False))
        elif args.release_assets and is_release(v):
            # The release asset is the record, so a cached copy is not trusted to be attached.
            if not download_release_docs(v, dest):
                builds.append((f"v{v}", v, dest, False))
        elif (dest / "index.html").is_file():
            print(f"Using {dest} for {v} (--rebuild to build it again)")
        else:
            builds.append((f"v{v}", v, dest, False))
    jobs = min(args.jobs, len(builds))
    print(f"Building {', '.join(b[1] for b in builds)} ({jobs} at a time)")
    OUTPUT.start([b[1] for b in builds])
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for job in [
            pool.submit(build_version, ref, tag, tags, dest, working)
            for ref, tag, dest, working in builds
        ]:
            job.result()
    if args.release_assets:
        for _, tag, dest, _ in builds[1:]:
            if is_release(tag):
                upload_release_docs(tag, dest)

    latest = next((v for v in versions if is_release(v)), None)
    print(f"Assembling the site in {out}, with {latest or DEV} at the root")
    for version in versions:
        shutil.copytree(archive / version, out / "v" / version)
    shutil.copytree(out / "v" / (latest or DEV), out, dirs_exist_ok=True)

    data = version_map(versions)
    pages = 0
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        new = set_version_map(text, data)
        if new != text:
            page.write_text(new, encoding="utf-8")
            pages += 1
    (out / "_version_map.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Set the version list on {pages} pages")
    stamp_path(out).write_text(json.dumps(built, indent=2) + "\n")
    print(f"Site ready in {out}")
    return out


def preview(args: argparse.Namespace) -> None:
    """Serves the site until interrupted, building it first unless it is up to date."""
    out: Path = args.out.resolve()
    versions = versions_of(existing_tags())
    path = stamp_path(out)
    current = path.is_file() and json.loads(path.read_text()) == stamp(
        args.ref, versions
    )
    if current and not (args.build or args.rebuild) and (out / "index.html").is_file():
        print(
            f"Site in {out} is up to date with {args.ref or 'the working tree'} and the tags (--build to build it again)"
        )
        site = out
    else:
        site = build(args, versions)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as e:
        raise DocsError(
            f"cannot serve on port {args.port} ({e.strerror}), try --port"
        ) from e
    with server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Serving {url} (Ctrl+C to stop)")
        if not args.no_open:
            webbrowser.open(url)
        server.serve_forever()


def parser() -> argparse.ArgumentParser:
    """Returns the command line parser."""
    p = argparse.ArgumentParser(
        prog="docs", description="Build and preview the docs site."
    )
    sub = p.add_subparsers(dest="command", required=True)
    for name, help in (
        ("build", "build the site"),
        ("preview", "serve the site, building it first unless it is up to date"),
    ):
        cmd = sub.add_parser(name, help=help)
        cmd.add_argument(
            "--ref",
            help="ref to build as dev (default: the working tree, uncommitted changes included)",
        )
        cmd.add_argument(
            "--jobs", type=int, default=os.cpu_count() or 1, help="parallel builds"
        )
        cmd.add_argument(
            "--rebuild", action="store_true", help="build archived tags again"
        )
        cmd.add_argument(
            "--release-assets",
            action="store_true",
            help=f"download release docs from, and attach new ones to, GitHub releases as {ASSET}",
        )
        cmd.add_argument(
            "--archive", type=Path, default=Path(ARCHIVE), help="tag docs cache"
        )
        cmd.add_argument(
            "--out", type=Path, default=Path(OUT), help="site output directory"
        )
        if name == "preview":
            cmd.add_argument("--port", type=int, default=8000)
            cmd.add_argument(
                "--build",
                action="store_true",
                help="build even if the site is up to date",
            )
            cmd.add_argument(
                "--no-open", action="store_true", help="do not open a browser"
            )
    return p


def main() -> None:
    """Runs the docs command."""
    args = parser().parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # pyright: ignore[reportAttributeAccessIssue]
    os.chdir(git("rev-parse", "--show-toplevel").strip())
    try:
        if args.command == "build":
            build(args)
        else:
            preview(args)
    except DocsError as e:
        sys.exit(f"docs: {e}")
    except KeyboardInterrupt:
        sys.exit("docs: stopped")
