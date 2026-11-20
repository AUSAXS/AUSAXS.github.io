"""Fetch the C++ documentation pages from the latest AUSAXS release.

The per-tool pages (command-line reference, developer notes) live in docs/ of https://github.com/AUSAXS/AUSAXS
and are versioned with the code, so the site shows the documentation of the latest *release*, not of master.
This script clones the release tag and copies docs/ into src/documentation/. The copies are git-ignored; the
site only owns src/documentation/index.md and citing.md.

While copying, each page gets
  - its front matter (title, description, ...) from scripts/docs_meta.yml,
  - an edit_url pointing at the page in the AUSAXS repository,
  - links to other site pages rewritten from https://ausaxs.github.io/... to relative .md links, so that
    `mkdocs build --strict` checks them.

Usage: python scripts/fetch_docs.py [--ref REF] [--repo URL_OR_PATH]
  --ref REF   Fetch this tag or branch instead of the latest release (or set AUSAXS_DOCS_REF). Useful for
              previewing documentation before it has been released, e.g. --ref master.
  --repo SRC  Clone from this URL or local path instead of GitHub, to test documentation changes.
Set GITHUB_TOKEN to avoid API rate limits when looking up the latest release.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import yaml

REPO = "AUSAXS/AUSAXS"
SITE_URL = "https://ausaxs.github.io/"
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DEST = SRC / "documentation"


def latest_release() -> str:
    request = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest", headers={"Accept": "application/vnd.github+json"})
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        return json.load(response)["tag_name"]


def clone(repo: str, ref: str, target: Path) -> None:
    subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", ref, repo, str(target)], check=True)


def site_link_to_relative(page: Path, match: re.Match) -> str:
    text, path, anchor = match.group("text"), match.group("path").strip("/"), match.group("anchor") or ""
    for candidate in (SRC / f"{path}.md", SRC / path / "index.md") if path else (SRC / "index.md",):
        if candidate.exists():
            relative = os.path.relpath(candidate, page.parent).replace(os.sep, "/")
            return f"[{text}]({relative}{anchor})"
    return match.group(0)  # not a page owned by the site, e.g. an asset


def front_matter(rel: str, meta: dict) -> str:
    fields = dict(meta.get(rel, {}))
    fields["edit_url"] = f"https://github.com/{REPO}/edit/master/docs/{rel}"
    return "---\n" + yaml.safe_dump(fields, sort_keys=False, allow_unicode=True, width=200) + "---\n\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ref", default=os.environ.get("AUSAXS_DOCS_REF"))
    parser.add_argument("--repo", default=f"https://github.com/{REPO}.git")
    args = parser.parse_args()
    ref = args.ref or latest_release()
    print(f"Fetching documentation from {REPO}@{ref}")

    meta = yaml.safe_load((ROOT / "scripts" / "docs_meta.yml").read_text())
    link = re.compile(r"\[(?P<text>[^\]]+)\]\(" + re.escape(SITE_URL) + r"(?P<path>[^)#\s]*)(?P<anchor>#[^)\s]*)?\)")

    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp) / "ausaxs"
        clone(args.repo, ref, checkout)
        docs = checkout / "docs"
        pages = sorted(docs.rglob("*.md")) if docs.is_dir() else []
        if not pages:
            print(f"error: {REPO}@{ref} has no docs/*.md pages. Pass --ref to fetch a branch that does.", file=sys.stderr)
            return 1

        # Replace the previous fetch: remove every directory the site does not own.
        for old in (p for p in DEST.iterdir() if p.is_dir()):
            shutil.rmtree(old)
        for page in pages:
            rel = page.relative_to(docs).as_posix()
            if rel not in meta:
                print(f"warning: {rel} has no entry in scripts/docs_meta.yml and is not in the navigation", file=sys.stderr)
            target = DEST / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(front_matter(rel, meta) + page.read_text(), encoding="utf-8")
        # links are rewritten once all pages exist, since they are resolved against the files on disk
        for page in pages:
            target = DEST / page.relative_to(docs)
            target.write_text(link.sub(lambda m: site_link_to_relative(target, m), target.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"Copied {len(pages)} pages into {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
