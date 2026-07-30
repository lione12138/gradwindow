from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.uzh.ch/de/studies/programs/master.html"
APPLICATION_URL = "https://www.uzh.ch/en/studies/application/master.html"
PATH_RE = re.compile(r"^/(?:de|en)/studies/programs/master/[^/]+\.html$")


class UZHAdapter(OfficialCatalogAdapter):
    university_id = "university-of-zurich-uzh"
    school_prefix = "uzh"
    institution_name = "University of Zurich"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 125

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        return [
            entry(
                name=link.get_text(" ", strip=True),
                degree_type="Master",
                source_url=link["href"],
                base_url=CATALOG_URL,
            )
            for link in soup.find_all("a", href=PATH_RE)
            if link.get_text(" ", strip=True)
        ]
