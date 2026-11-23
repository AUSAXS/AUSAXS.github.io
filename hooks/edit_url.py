"""Let a page's front matter set its edit link.

The reference pages fetched by scripts/fetch_docs.py are edited in their own repositories, so the fetch script writes
an `edit_url` into their front matter. MkDocs ignores that key and builds the link from `edit_uri`, which points at
this repository, so it is applied here instead.
"""


def on_page_markdown(markdown: str, page, **kwargs) -> str:
    if url := page.meta.get("edit_url"):
        page.edit_url = url
    return markdown
