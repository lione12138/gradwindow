from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.rug.nl/masters/alphabetical?lang=en"
APPLICATION_URL = "https://www.rug.nl/masters/admission-and-application/"
PATH_RE = re.compile(r"^/masters/[^/?#]+/?$")
EXCLUDED = {
    "in-english",
    "alphabetical",
    "by-subject",
    "by-faculty",
    "research-masters",
}


class GroningenAdapter(OfficialCatalogAdapter):
    university_id = "university-of-groningen"
    school_prefix = "groningen"
    institution_name = "University of Groningen"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 200

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            key = link["href"].strip("/").split("/")[-1]
            name = link.get_text(" ", strip=True)
            if key in EXCLUDED or not name:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
