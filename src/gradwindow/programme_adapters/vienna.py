from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://studieren.univie.ac.at/en/degree-programmes/master-programmes/"
APPLICATION_URL = (
    "https://studieren.univie.ac.at/en/admission-procedure/master-programmes/"
)
PATH_RE = re.compile(r"^/en/degree-programmes/master-programmes/[^/?#]+/?$")


class ViennaAdapter(OfficialCatalogAdapter):
    university_id = "university-of-vienna"
    school_prefix = "vienna"
    institution_name = "University of Vienna"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 105

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        return [
            entry(
                name=link.get_text(" ", strip=True).removesuffix(" (Master)"),
                degree_type="Master",
                source_url=link["href"],
                base_url=CATALOG_URL,
            )
            for link in soup.find_all("a", href=PATH_RE)
            if link.get_text(" ", strip=True).endswith("(Master)")
        ]
