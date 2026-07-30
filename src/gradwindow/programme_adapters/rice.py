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
    "https://ga.rice.edu/graduate-students/academic-opportunities/degree-chart/"
)
APPLICATION_URL = "https://graduate.rice.edu/admissions/how-apply"


class RiceAdapter(OfficialCatalogAdapter):
    university_id = "rice-university"
    school_prefix = "rice"
    institution_name = "Rice University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 75
    retrieval_method = "official-degree-chart"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for row in soup.select("table tr"):
            name = row.get_text(" ", strip=True)
            link = row.find("a", href=True)
            if link is None or not re.search(r"\bMaster of", name):
                continue
            name = name.removesuffix(" *").strip()
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
