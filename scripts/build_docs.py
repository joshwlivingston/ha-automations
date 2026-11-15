"""Build the docs site with a version selector.

Each release tag (vX.Y.Z) builds once from its own checkout and is kept in the archive directory
as ARCHIVE/X.Y.Z/. Later runs reuse it, so a run builds only the dev ref and releases missing from
the archive. The site puts the newest release at the root, every release under v/X.Y.Z/ and the
dev ref under v/dev/. The version list baked into each page is rewritten so every page lists every
version.

Usage: uv run --no-project scripts/build_docs.py [--archive DIR] [--out DIR] [--ref REF]
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
VERSION_META = re.compile(r'<meta name="gd-version-map" content="[^"]*">')
DEV = "dev"
# Build output that only applies to a full Great Docs versioned site.
DROP = ["v", "_redirects", "vercel.json", "_version_map.json"]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def releases() -> list[str]:
    """Return release versions, newest first."""
    found = [
        m for t in git("tag", "--list", "v*").split() if (m := RELEASE_TAG.fullmatch(t))
    ]
    found.sort(key=lambda m: tuple(int(g) for g in m.groups()), reverse=True)
    return [m.group(0)[1:] for m in found]


def build(ref: str, tag: str, tags: list[str], dest: Path) -> None:
    """Build the docs at ref as version tag into dest."""
    print(f"Building docs for {tag} from {ref}", flush=True)
    # Listing every version makes Great Docs add the selector; tag is latest so it builds at the root.
    versions = [{"tag": t, "label": t, "latest": t == tag} for t in tags]
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tree"
        git("worktree", "add", "--quiet", "--detach", str(tree), ref)
        try:
            with open(tree / "great-docs.yml", "a") as f:
                f.write(f"\nversions: {json.dumps(versions)}\n")
            for cmd in (
                ["uv", "sync", "--quiet", "--locked", "--group", "docs"],
                ["uv", "run", "--no-sync", "great-docs", "build", "--latest-only"],
            ):
                subprocess.run(cmd, cwd=tree, env=env, check=True)
            site = tree / "great-docs" / "_site"
            for name in DROP:
                path = site / name
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(site, dest)
        finally:
            git("worktree", "remove", "--force", str(tree))


def version_map(versions: list[str]) -> dict[str, object]:
    """Return the selector's version map: dev, then releases with the newest as latest."""
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the docs site with a version selector."
    )
    parser.add_argument("--archive", type=Path, default=ROOT / ".docs-archive")
    parser.add_argument("--out", type=Path, default=ROOT / "great-docs" / "_site")
    parser.add_argument("--ref", default="HEAD", help="ref to build as dev")
    args = parser.parse_args()
    archive: Path = args.archive.resolve()
    out: Path = args.out.resolve()

    versions = releases()
    tags = [DEV, *versions]
    archive.mkdir(parents=True, exist_ok=True)
    for version in versions:
        if not (archive / version).is_dir():
            build(f"v{version}", version, tags, archive / version)

    if out.exists():
        shutil.rmtree(out)
    build(args.ref, DEV, tags, out / "v" / DEV)
    for version in versions:
        shutil.copytree(archive / version, out / "v" / version)
    shutil.copytree(
        out / "v" / (versions[0] if versions else DEV), out, dirs_exist_ok=True
    )

    data = version_map(versions)
    meta = f'<meta name="gd-version-map" content="{html.escape(json.dumps(data, separators=(",", ":")))}">'
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        new = VERSION_META.sub(lambda _: meta, text)
        if new != text:
            page.write_text(new, encoding="utf-8")
    (out / "_version_map.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Site ready in {out}")


if __name__ == "__main__":
    main()
