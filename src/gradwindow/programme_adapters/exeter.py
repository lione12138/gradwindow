from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.exeter.ac.uk/study/postgraduate/courses/"
APPLICATION_URL = "https://www.exeter.ac.uk/study/postgraduate/applying/"
PATH_RE = re.compile(r"^(?:https://www\.exeter\.ac\.uk)?/masters-degrees/[^/?#]+/?$")


class ExeterAdapter(OfficialCatalogAdapter):
    university_id = "university-of-exeter"
    school_prefix = "exeter"
    institution_name = "University of Exeter"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 140

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            name = link.get_text(" ", strip=True)
            degree = degree_from(name, default="")
            if not degree:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree,
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
