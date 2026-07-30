from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.uio.no/english/studies/programmes/"
APPLICATION_URL = "https://www.uio.no/english/studies/admission/master/"
PATH_RE = re.compile(r"^https://www\.uio\.no/english/studies/programmes/[^/?#]+/?$")


class OsloAdapter(OfficialCatalogAdapter):
    university_id = "university-of-oslo"
    school_prefix = "oslo"
    institution_name = "University of Oslo"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 55

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            name = link.get_text(" ", strip=True)
            slug = urlparse(link["href"]).path.rstrip("/").split("/")[-1]
            if "master" not in name.lower() and "master" not in slug.lower():
                continue
            entries.append(
                entry(
                    name=re.sub(r"\s*\(master\)$", "", name, flags=re.I),
                    degree_type="Master",
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
