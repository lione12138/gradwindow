from __future__ import annotations

import copy
import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://gradcatalog.ufl.edu/graduate/degrees/table/"
APPLICATION_URL = "https://grad.ufl.edu/apply/"


class FloridaAdapter(OfficialCatalogAdapter):
    university_id = "university-of-florida"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "florida"
    institution_name = "University of Florida"
    minimum_expected_programmes = 170
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-graduate-degree-table"
    catalogue_limitation_reason = (
        "Florida's official degree table is complete, but application windows "
        "are published by individual programmes and do not share one exact pair "
        "of opening and closing dates."
    )

    def __init__(self, minimum_expected_programmes: int = 170) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for heading in soup.select("h3"):
            raw_degree = normalise(heading.get_text(" ", strip=True))
            if not raw_degree.startswith("Master of"):
                continue
            degree_type = re.sub(r"\s+[TN](?:/[TN])?$", "", raw_degree).strip()
            listing = heading.find_next_sibling("ul")
            if listing is None:
                continue
            for item in listing.select(":scope > li"):
                clean = copy.copy(item)
                for nested in clean.select("ul, sup"):
                    nested.decompose()
                name = normalise(clean.get_text(" ", strip=True))
                if name:
                    rows.append(
                        CatalogEntry(
                            name=name,
                            degree_type=degree_type,
                            source_url=CATALOG_URL,
                        )
                    )
        return rows
