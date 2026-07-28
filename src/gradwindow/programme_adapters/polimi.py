from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "politecnico-di-milano"
CATALOG_URL = "https://www.polimi.it/en/education/laurea-magistrale-programmes"
APPLICATION_URL = (
    "https://www.polimi.it/en/prospective-students/how-to-apply/"
    "admission-to-laurea-magistrale/foreign-qualification/deadlines"
)
PROGRAMME_PATH = "/en/education/laurea-magistrale-programmes/programme-detail/"


class PolimiAdapter(BaseProgrammeAdapter):
    """Discover Politecnico di Milano Laurea Magistrale programmes."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 40) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select(f'a[href*="{PROGRAMME_PATH}"]'):
            name_node = link.select_one(".localised-title-title")
            if name_node is None:
                continue
            name = _normalise(name_node.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            slug = urlsplit(source_url).path.rstrip("/").rsplit("/", 1)[-1]
            campus_node = link.select_one(".campusName")
            campus = (
                _normalise(campus_node.get_text(" ", strip=True)) if campus_node else ""
            )
            programme_id = f"polimi-{slug}-laurea-magistrale"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Laurea Magistrale",
                faculty="Politecnico di Milano",
                department=campus,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Politecnico di Milano's official Laurea Magistrale catalogue "
                    "confirms this programme. Admission calls vary by study area, "
                    "qualification and intake; no date pair is assigned without a "
                    "deterministic scope match."
                ),
                parse_status="no-deadline",
                retrieval_method="official-programme-catalogue",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Politecnico di Milano's official catalogue contained "
                f"{len(result)} Laurea Magistrale programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
