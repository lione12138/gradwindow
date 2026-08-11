from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://international.huji.ac.il/huji_programs"
APPLICATION_URL = "https://registration.huji.ac.il/en/"
MASTER_LABEL_RE = re.compile(
    r"(?:\bM\.?A\.?\b|\bMSc\b|\bLL\.?M\.?\b|\bInternational Master\b)",
    re.IGNORECASE,
)


class HebrewAdapter(OfficialCatalogAdapter):
    university_id = "hebrew-university-of-jerusalem"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "hebrew"
    institution_name = "Hebrew University of Jerusalem"
    minimum_expected_programmes = 10
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-programmes-table"
    catalogue_limitation_reason = (
        "Hebrew University's official international catalogue identifies its "
        "English-language master's programmes. The university routes applicants "
        "to programme-specific admissions guidance, so no common exact window is "
        "inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 10) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        for table_row in soup.select("table tr"):
            link = table_row.select_one("a[href]")
            if link is None:
                continue
            label = normalise(link.get_text(" ", strip=True))
            if not MASTER_LABEL_RE.search(label):
                continue
            degree_type = "Master"
            compact = label.replace(".", "")
            for token in ("LLM", "MSc", "MA"):
                if re.search(rf"\b{token}\b", compact, re.IGNORECASE):
                    degree_type = token
                    break
            rows.append(
                CatalogEntry(
                    name=label,
                    degree_type=degree_type,
                    source_url=str(link["href"]),
                )
            )
        return rows
