from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.ncl.ac.uk/postgraduate/degrees/"
APPLICATION_URL = "https://www.ncl.ac.uk/postgraduate/applications-offers/"
PATH_RE = re.compile(r"^(?:https://www\.ncl\.ac\.uk)?/postgraduate/degrees/[^/?#]+/?$")


class NewcastleAdapter(OfficialCatalogAdapter):
    university_id = "newcastle-university"
    school_prefix = "newcastle"
    institution_name = "Newcastle University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 175

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            name = link.get_text(" ", strip=True)
            lower = name.lower()
            degree = degree_from(name, default="")
            if not degree or any(
                value in lower for value in ("phd", "mphil", "dprof", "pgcert", "pgdip")
            ):
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
