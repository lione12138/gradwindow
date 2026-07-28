from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "ruprecht-karls-universit-t-heidelberg"
CATALOG_URL = "https://www.uni-heidelberg.de/en/study/all-subjects"
APPLICATION_URL = "https://www.uni-heidelberg.de/en/study/application-enrolment"
EXISTING_DATA_COMPUTER_SCIENCE_ID = "heidelberg-data-and-computer-science-master"


class HeidelbergAdapter(BaseProgrammeAdapter):
    """Discover Heidelberg master variants from the official subjects list."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 110) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for card in soup.select("section"):
            title_node = card.select_one("h4")
            if title_node is None:
                continue
            subject = _normalise(title_node.get_text(" ", strip=True))
            for link in card.find_all("a", href=True):
                degree = _normalise(link.get_text(" ", strip=True))
                if "master" not in degree.lower():
                    continue
                source_url = urljoin(CATALOG_URL, str(link["href"]))
                slug = urlsplit(source_url).path.rstrip("/").rsplit("/", 1)[-1]
                programme_id = f"heidelberg-{slug}"
                if "data-and-computer-science" in source_url and "master" in slug:
                    programme_id = EXISTING_DATA_COMPUTER_SCIENCE_ID
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=f"{subject} — {degree}",
                    degree_type="MEd" if "education" in degree.lower() else "Master",
                    faculty="Heidelberg University",
                    department=subject,
                    source_url=source_url,
                    application_url=source_url,
                    windows=[],
                    deadline_text=(
                        "Heidelberg University's official subjects catalogue "
                        "confirms this master's variant. Application procedures "
                        "and deadlines vary by subject; no exact date pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-subject-catalogue",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Heidelberg's official subjects list contained "
                f"{len(result)} master's variants; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
