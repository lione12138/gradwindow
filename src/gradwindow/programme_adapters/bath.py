from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = (
    "https://www.bath.ac.uk/courses/postgraduate-2026/taught-postgraduate-courses/"
)
APPLICATION_URL = (
    "https://www.bath.ac.uk/guides/applying-for-a-taught-postgraduate-course/"
)
PATH_RE = re.compile(
    r"^/courses/postgraduate-2026/taught-postgraduate-courses/[^/?#]+/?$"
)


class BathAdapter(OfficialCatalogAdapter):
    university_id = "university-of-bath"
    school_prefix = "bath"
    institution_name = "University of Bath"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 75

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            name = link.get_text(" ", strip=True).split(" – ", 1)[0]
            if degree_from(name, default="") == "":
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
