"""Build and preview the ha-automations docs site with a version selector.

Usage:
    uv run docs build     build the site into great-docs/_site
    uv run docs preview   build the site and serve it locally

Each release tag (vX.Y.Z) builds once from its own checkout and is kept in the archive directory
as ARCHIVE/X.Y.Z/. A build builds the dev ref and any release whose archived docs are missing, and
drops archived docs for tags that no longer exist. Builds run in parallel. The site puts the
newest release at the root, every release under v/X.Y.Z/ and the dev ref under v/dev/. The
version list baked into each page is rewritten so every page lists every version.
"""

import argparse
import functools
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RELEASE_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
VERSION_META = re.compile(r'<meta name="gd-version-map" content="[^"]*">')
DEV = "dev"
ARCHIVE = ".docs-archive"
OUT = "great-docs/_site"
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


def releases(tags: list[str]) -> list[str]:
    """Returns the release versions among tags, newest first."""
    found = [m for t in tags if (m := RELEASE_TAG.fullmatch(t))]
    found.sort(key=lambda m: tuple(int(g) for g in m.groups()), reverse=True)
    return [m.group(0)[1:] for m in found]


def version_map(versions: list[str]) -> dict[str, object]:
    """Returns the selector's version map: dev, then releases with the newest as latest."""
    entries: list[dict[str, object]] = [
        {"tag": DEV, "label": DEV, "path_prefix": f"v/{DEV}", "prerelease": True}
    ]
    for i, version in enumerate(versions):
        entry: dict[str, object] = {"tag": version, "label": version}
        if i == 0:
            entry |= {"latest": True, "path_prefix": ""}
        else:
            entry["path_prefix"] = f"v/{version}"
        entries.append(entry)
    return {"versions": entries, "pages": {}}


def set_version_map(page: str, data: dict[str, object]) -> str:
    """Returns page with its version map meta tag set to data."""
    content = html.escape(json.dumps(data, separators=(",", ":")))
    meta = f'<meta name="gd-version-map" content="{content}">'
    return VERSION_META.sub(lambda _: meta, page)


def build_version(ref: str, tag: str, tags: list[str], dest: Path) -> None:
    """Builds the docs at ref as version tag into dest. Output goes to a log shown on failure."""
    start = time.monotonic()
    # Listing every version makes Great Docs add the selector; tag is latest so it builds at the root.
    versions = [{"tag": t, "label": t, "latest": t == tag} for t in tags]
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tree"
        log = Path(tmp) / "build.log"
        with GIT_LOCK:
            git("worktree", "add", "--quiet", "--detach", str(tree), ref)
        try:
            with open(tree / "great-docs.yml", "a") as f:
                f.write(f"\nversions: {json.dumps(versions)}\n")
            with open(log, "w") as out:
                for cmd in (
                    ["uv", "sync", "--quiet", "--locked", "--group", "docs"],
                    ["uv", "run", "--no-sync", "great-docs", "build", "--latest-only"],
                ):
                    result = subprocess.run(
                        cmd, check=False, cwd=tree, env=env, stdout=out, stderr=out
                    )
                    if result.returncode:
                        print(log.read_text())
                        raise DocsError(f"build of {tag} from {ref} failed")
            site = tree / "great-docs" / "_site"
            for name in DROP:
                path = site / name
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            # Copy then rename, so a failed copy never leaves a partial dest.
            partial = dest.with_name(dest.name + ".partial")
            for path in (partial, dest):
                if path.exists():
                    shutil.rmtree(path)
            shutil.copytree(site, partial)
            partial.rename(dest)
        finally:
            with GIT_LOCK:
                git("worktree", "remove", "--force", str(tree))
    print(f"Built {tag} from {ref} in {time.monotonic() - start:.0f}s")


def build(args: argparse.Namespace) -> Path:
    """Builds the site and returns its directory."""
    archive: Path = args.archive.resolve()
    out: Path = args.out.resolve()
    versions = releases(git("tag", "--list", "v*").split())
    tags = [DEV, *versions]

    archive.mkdir(parents=True, exist_ok=True)
    # Drop archived docs for tags that no longer exist and leftovers from failed copies.
    for path in archive.iterdir():
        if (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in versions
        ):
            shutil.rmtree(path)
    if out.exists():
        shutil.rmtree(out)

    builds = [(args.ref, DEV, out / "v" / DEV)]
    # Rebuild any release whose archived docs are missing or incomplete.
    builds += [
        (f"v{v}", v, archive / v)
        for v in versions
        if not (archive / v / "index.html").is_file()
    ]
    print("Building " + ", ".join(tag for _, tag, _ in builds))
    with ThreadPoolExecutor(max_workers=min(args.jobs, len(builds))) as pool:
        for job in [
            pool.submit(build_version, ref, tag, tags, dest)
            for ref, tag, dest in builds
        ]:
            job.result()

    for version in versions:
        shutil.copytree(archive / version, out / "v" / version)
    shutil.copytree(
        out / "v" / (versions[0] if versions else DEV), out, dirs_exist_ok=True
    )

    data = version_map(versions)
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        new = set_version_map(text, data)
        if new != text:
            page.write_text(new, encoding="utf-8")
    (out / "_version_map.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Site ready in {out}")
    return out


def preview(args: argparse.Namespace) -> None:
    """Builds the site and serves it until interrupted."""
    site = build(args)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
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
        ("preview", "build and serve the site"),
    ):
        cmd = sub.add_parser(name, help=help)
        cmd.add_argument(
            "--ref", default="HEAD", help="ref to build as dev (default HEAD)"
        )
        cmd.add_argument(
            "--jobs", type=int, default=os.cpu_count() or 1, help="parallel builds"
        )
        cmd.add_argument(
            "--archive", type=Path, default=Path(ARCHIVE), help="release docs cache"
        )
        cmd.add_argument(
            "--out", type=Path, default=Path(OUT), help="site output directory"
        )
        if name == "preview":
            cmd.add_argument("--port", type=int, default=8000)
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
