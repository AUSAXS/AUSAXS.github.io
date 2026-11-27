"""Write sitemap.txt, a plain-text copy of sitemap.xml with one URL per line.

Google Search Console keeps reporting the valid sitemap.xml as "could not be read". Google also accepts plain-text
sitemaps, so this one is submitted next to it to tell apart a problem with the XML from one on Google's side. It is
built from the finished sitemap.xml, so both always list the same pages.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def on_post_build(config, **kwargs):
    site = Path(config.site_dir)
    urls = [loc.text.strip() for loc in ET.parse(site / "sitemap.xml").getroot().iter(f"{NS}loc")]
    (site / "sitemap.txt").write_text("".join(f"{url}\n" for url in urls), encoding="utf-8")
