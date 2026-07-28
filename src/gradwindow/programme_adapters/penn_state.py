from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "pennsylvania-state-university"
CATALOG_URL = "https://bulletins.psu.edu/graduate-professional-programs/"
APPLICATION_URL = "https://gradschool.psu.edu/graduate-admissions/how-to-apply/"
EXISTING_COMPUTER_SCIENCE_ID = "penn-state-computer-science-engineering-ms"


class PennStateAdapter(BaseProgrammeAdapter):
    """Discover Penn State programmes tagged as master's degrees."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 140) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in soup.select("li.item"):
            keywords = {
                _normalise(node.get_text(" ", strip=True))
                for node in item.select(".keyword")
            }
            if "Master's Degrees" not in keywords:
                continue
            title_node = item.select_one(".title")
            link = item.find("a", href=True)
            if title_node is None or link is None:
                continue
            name = _normalise(title_node.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            slug = urlsplit(source_url).path.rstrip("/").rsplit("/", 1)[-1]
            programme_id = f"penn-state-{slug}-master"
            if slug == "computer-science-engineering":
                programme_id = EXISTING_COMPUTER_SCIENCE_ID
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Penn State",
                department="Penn State",
                source_url=source_url,
                application_url=source_url,
                windows=[],
                deadline_text=(
                    "Penn State's official graduate-programme directory identifies "
                    "this programme as offering a master's degree. Requirements "
                    "and deadlines vary by programme; no exact date pair is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-graduate-programme-directory",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Penn State's official programme directory contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
