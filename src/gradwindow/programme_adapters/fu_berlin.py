from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.fu-berlin.de/studium/studienangebot/master/index.html"
APPLICATION_URL = "https://www.fu-berlin.de/en/studium/bewerbung/master/index.html"
PATH_RE = re.compile(r"^/studium/studienangebot/master/[^/]+/index\.html$")


class FUBerlinAdapter(OfficialCatalogAdapter):
    university_id = "freie-universit-t-berlin"
    school_prefix = "fu-berlin"
    institution_name = "Freie Universität Berlin"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 90

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
            if "/master/gemeinsame/" not in link["href"]
        ]
