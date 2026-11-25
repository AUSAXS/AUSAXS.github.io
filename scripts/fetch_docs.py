"""Fetch the reference documentation from the latest releases of AUSAXS and pyAUSAXS.

The reference pages live in docs/ of each code repository and are versioned with the code, so the site shows the
documentation of the latest *release*, not of master:
  - https://github.com/AUSAXS/AUSAXS     docs/ -> src/documentation/       (command-line tools, developer notes)
  - https://github.com/AUSAXS/pyAUSAXS   docs/ -> src/pyausaxs/reference/  (Python API reference)
This script clones the release tag of each and copies its docs/ into the site. The copies are git-ignored; the site
only owns the files listed as `owned` below.

While copying, each page gets
  - its front matter (title, description, ...) from scripts/docs_meta.yml,
  - an edit_url pointing at the page in its repository,
  - links to other site pages rewritten from https://ausaxs.github.io/... to relative .md links, so that
    `mkdocs build --strict` checks them.

Usage: python scripts/fetch_docs.py [--source NAME] [--ref REF] [--repo URL_OR_PATH]
  --source NAME  Only fetch one source, `ausaxs` or `pyausaxs`. Default: both.
  --ref REF      Fetch this tag or branch instead of the latest release. Useful for previewing documentation before
                 it has been released, e.g. --ref master. Needs --source.
  --repo SRC     Clone from this URL or local path instead of GitHub, to test documentation changes. Needs --source.
The environment variables AUSAXS_DOCS_REF / PYAUSAXS_DOCS_REF and AUSAXS_DOCS_REPO / PYAUSAXS_DOCS_REPO do the same
per source. Set GITHUB_TOKEN to avoid API rate limits when looking up the latest release.
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
from dataclasses import dataclass
from pathlib import Path

import yaml

SITE_URL = "https://ausaxs.github.io/"
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


@dataclass
class Source:
    name: str          # command-line name and environment variable prefix
    repo: str          # GitHub owner/name
    branch: str        # default branch, for the edit links
    dest: Path         # where docs/ is copied to
    owned: tuple = ()  # files in dest that belong to the site and are kept

    def env(self, suffix: str) -> str | None:
        return os.environ.get(f"{self.name.upper()}_DOCS_{suffix}")


SOURCES = [
    Source("ausaxs", "AUSAXS/AUSAXS", "master", SRC / "documentation", owned=("index.md", "citing.md")),
    Source("pyausaxs", "AUSAXS/pyAUSAXS", "master", SRC / "pyausaxs" / "reference"),
]


def latest_release(repo: str) -> str:
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest", headers={"Accept": "application/vnd.github+json"})
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


def front_matter(source: Source, rel: str, meta: dict) -> str:
    fields = dict(meta.get(rel, {}))
    fields["edit_url"] = f"https://github.com/{source.repo}/edit/{source.branch}/docs/{rel}"
    return "---\n" + yaml.safe_dump(fields, sort_keys=False, allow_unicode=True, width=200) + "---\n\n"


def fetch(source: Source, ref: str | None, repo: str | None, meta: dict) -> list[Path]:
    """Copy docs/ of the source into its destination, and return the copied pages."""
    ref = ref or source.env("REF") or latest_release(source.repo)
    repo = repo or source.env("REPO") or f"https://github.com/{source.repo}.git"
    print(f"Fetching documentation from {source.repo}@{ref}" + (f" ({repo})" if not repo.startswith("https://") else ""))

    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp) / source.name
        clone(repo, ref, checkout)
        docs = checkout / "docs"
        pages = sorted(docs.rglob("*.md")) if docs.is_dir() else []
        if not pages:
            raise SystemExit(f"error: {source.repo}@{ref} has no docs/*.md pages. Pass --ref to fetch a branch that does.")

        # Replace the previous fetch: remove everything the site does not own.
        source.dest.mkdir(parents=True, exist_ok=True)
        for old in source.dest.iterdir():
            if old.name in source.owned:
                continue
            shutil.rmtree(old) if old.is_dir() else old.unlink()
        targets = []
        for page in pages:
            rel = page.relative_to(docs).as_posix()
            if rel not in meta:
                print(f"warning: {rel} has no entry for {source.repo} in scripts/docs_meta.yml and is not in the navigation", file=sys.stderr)
            target = source.dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(front_matter(source, rel, meta) + page.read_text(encoding="utf-8"), encoding="utf-8")
            targets.append(target)
    print(f"Copied {len(pages)} pages into {source.dest.relative_to(ROOT)}")
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=[s.name for s in SOURCES])
    parser.add_argument("--ref")
    parser.add_argument("--repo")
    args = parser.parse_args()
    if (args.ref or args.repo) and not args.source:
        parser.error("--ref and --repo need --source")

    meta = yaml.safe_load((ROOT / "scripts" / "docs_meta.yml").read_text())
    pages = []
    for source in SOURCES:
        if args.source in (None, source.name):
            pages += fetch(source, args.ref, args.repo, meta.get(source.repo, {}))

    # links are rewritten once all pages exist, since they are resolved against the files on disk
    link = re.compile(r"\[(?P<text>[^\]]+)\]\(" + re.escape(SITE_URL) + r"(?P<path>[^)#\s]*)(?P<anchor>#[^)\s]*)?\)")
    for target in pages:
        target.write_text(link.sub(lambda m: site_link_to_relative(target, m), target.read_text(encoding="utf-8")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
