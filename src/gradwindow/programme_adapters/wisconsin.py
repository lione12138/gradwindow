from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://guide.wisc.edu/graduate/"
APPLICATION_URL = "https://grad.wisc.edu/apply/"
PROGRAMME_PATH_RE = re.compile(r"^/graduate/[^/]+/[^/]+/?$")
MASTER_AWARDS = {
    "ma",
    "macc",
    "meng",
    "mfa",
    "mipa",
    "mm",
    "mpa",
    "mba",
    "ms",
    "msw",
}


class WisconsinAdapter(OfficialCatalogAdapter):
    university_id = "university-of-wisconsin-madison"
    school_prefix = "wisconsin"
    institution_name = "University of Wisconsin–Madison"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 150

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PROGRAMME_PATH_RE):
            path = urlparse(link["href"]).path.rstrip("/")
            award = path.split("/")[-1].rsplit("-", 1)[-1]
            if award not in MASTER_AWARDS:
                continue
            title = link.select_one(".title.visual") or link.find("h3")
            if title is None:
                continue
            entries.append(
                entry(
                    name=title.get_text(" ", strip=True),
                    degree_type=award.upper(),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
