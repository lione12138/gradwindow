from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://uwaterloo.ca/future-graduate-students/programs"
APPLICATION_URL = (
    "https://uwaterloo.ca/future-graduate-students/admissions/how-to-apply"
)
PATH_RE = re.compile(r"^/future-graduate-students/programs/by-faculty/.+")


class WaterlooAdapter(OfficialCatalogAdapter):
    university_id = "university-of-waterloo"
    school_prefix = "waterloo"
    institution_name = "University of Waterloo"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 100

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            name = link.get_text(" ", strip=True)
            lower = name.lower()
            if "master" not in lower or any(
                value in lower for value in ("doctoral", "phd", "graduate diploma")
            ):
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
