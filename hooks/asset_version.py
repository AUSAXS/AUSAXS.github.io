"""Version the site's own scripts and stylesheets, so that a deploy is not mixed with old files.

GitHub Pages serves every file with `Cache-Control: max-age=600`. Material's own assets carry a hash in their name, but
src/javascripts and src/stylesheets do not, so for ten minutes after a deploy a browser could pair a new page or script
with the old stylesheet, e.g. show the Run buttons of run-python.js unstyled. Their links get `?v=<hash>` instead, a
hash of the contents of both folders, which changes with any of their files. run-python.js passes its version on to the
worker, and the worker to the files it fetches.
"""

import hashlib
import re
from pathlib import Path

FOLDERS = ("javascripts", "stylesheets")
version = ""


def on_config(config, **kwargs):
    global version
    digest = hashlib.sha256()
    for folder in FOLDERS:
        for path in sorted((Path(config.docs_dir) / folder).rglob("*")):
            if path.is_file():
                digest.update(path.relative_to(config.docs_dir).as_posix().encode())
                digest.update(path.read_bytes())
    version = digest.hexdigest()[:10]
    return config


# a link to a file of one of the folders, relative or from the root, without a query, in a src or href attribute
LINK = re.compile(r'((?:src|href)=")((?:/|(?:\.\./)*)(?:%s)/[^"?#:]+\.(?:js|css))"' % "|".join(FOLDERS))


def on_post_page(output: str, **kwargs) -> str:
    return LINK.sub(rf'\1\2?v={version}"', output)


def on_post_template(output: str, **kwargs) -> str:
    # the static templates, such as 404.html, which are not pages
    return on_post_page(output)
