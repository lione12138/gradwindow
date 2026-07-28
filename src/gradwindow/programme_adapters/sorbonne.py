from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "sorbonne-university-merged-from-paris-iv-and-upmc"
CATALOG_URL = "https://www.sorbonne-universite.fr/en/programs-english"
APPLICATION_URL = "https://www.sorbonne-universite.fr/en/admissions"
EXISTING_COMPUTER_SCIENCE_ID = "sorbonne-computer-science-master"


class SorbonneAdapter(BaseProgrammeAdapter):
    """Discover Sorbonne University's English-taught master's programmes."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 6) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for heading in soup.select(".field-collapse__trigger h3"):
            name = _normalise(heading.get_text(" ", strip=True))
            if not name:
                continue
            programme_id = f"sorbonne-{_slug(name)}-master"
            if "computer science" in name.lower():
                programme_id = EXISTING_COMPUTER_SCIENCE_ID
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Sorbonne University",
                department="Sorbonne University",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Sorbonne University's official English-programme catalogue "
                    "confirms this master's programme. Admissions routes and dates "
                    "vary by faculty and programme; no exact opening-and-closing "
                    "pair is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-programme-page",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Sorbonne's official English catalogue contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
