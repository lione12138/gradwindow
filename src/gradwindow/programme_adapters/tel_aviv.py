from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://international.tau.ac.il/fees_and_expenses?tab=3"
APPLICATION_URL = "https://international.tau.ac.il/Degree_Programs"
DEGREE_RE = re.compile(r"\b(MA|MDM|MBA|MFA|MMus|LLM|MSc)\b", re.IGNORECASE)


class TelAvivAdapter(OfficialCatalogAdapter):
    university_id = "tel-aviv-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "tel-aviv"
    institution_name = "Tel Aviv University"
    minimum_expected_programmes = 23
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-graduate-fee-table"
    catalogue_limitation_reason = (
        "Tel Aviv University's official international fee table enumerates the "
        "currently offered international graduate degrees and links to their "
        "programme pages. Programme-specific exact application windows are not "
        "published in that central table."
    )

    def __init__(self, minimum_expected_programmes: int = 23) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        if not tables:
            return []
        rows: list[CatalogEntry] = []
        for table_row in tables[0].select("tr"):
            link = table_row.select_one("a[href]")
            if link is None:
                continue
            row_text = normalise(table_row.get_text(" ", strip=True))
            degree_match = DEGREE_RE.search(row_text)
            if degree_match is None:
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(link.get_text(" ", strip=True)),
                    degree_type=degree_match.group(1),
                    source_url=str(link["href"]),
                )
            )
        return rows
