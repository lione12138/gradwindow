from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.weizmann.ac.il/wsos/admissions/about-msc-tracks"
APPLICATION_URL = CATALOG_URL
PROGRAMME_NAMES = {
    "Physics": "Physical Sciences",
    "Chemistry": "Chemical Sciences",
    "Math & CS": "Mathematics and Computer Science",
    "Science Teaching": "Science Teaching",
    "Life Sciences": "Life Sciences",
}


class WeizmannAdapter(OfficialCatalogAdapter):
    university_id = "weizmann-institute-of-science"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "weizmann"
    institution_name = "Weizmann Institute of Science"
    minimum_expected_programmes = 5
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-msc-programmes-page"
    catalogue_limitation_reason = (
        "Weizmann's official MSc page lists its five research fields and tracks. "
        "The page publishes programme-specific admissions guidance rather than one "
        "complete exact opening-and-closing date pair."
    )

    def __init__(self, minimum_expected_programmes: int = 5) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for heading in soup.select("h3.field-of-study-wrapper"):
            label = normalise(heading.get_text(" ", strip=True))
            name = PROGRAMME_NAMES.get(label)
            if name is None:
                continue
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="MSc",
                    source_url=CATALOG_URL,
                )
            )
        return rows
