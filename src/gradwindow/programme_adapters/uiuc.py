from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "university-of-illinois-at-urbana-champaign"
CATALOG_URL = "https://catalog.illinois.edu/degree-programs/graduate_index/"
APPLICATION_URL = "https://grad.illinois.edu/admissions/apply"
EXISTING_COMPUTER_SCIENCE_ID = "uiuc-computer-science-ms"
MASTER_AWARDS = {
    "AD",
    "EDM",
    "IMBA",
    "LLM",
    "MA",
    "MAAE",
    "MANSC",
    "MARCH",
    "MAS",
    "MATESL",
    "MBA",
    "MCS",
    "MDES",
    "MENG",
    "MFA",
    "MHA",
    "MHRIR",
    "MLA",
    "MME",
    "MMUS",
    "MPH",
    "PSM",
    "MS",
    "MSA",
    "MSL",
    "MSUD",
    "MSW",
    "MUP",
    "MVS",
}


class UIUCAdapter(BaseProgrammeAdapter):
    """Discover master's awards from Illinois' official graduate index."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 160) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for row in soup.select("table.tbl_degreeprograms tbody tr"):
            name_node = row.select_one("td.column0")
            faculty_node = row.select_one("td.column1")
            if name_node is None:
                continue
            base_name = _normalise(name_node.get_text(" ", strip=True))
            faculty = (
                _normalise(faculty_node.get_text(" ", strip=True))
                if faculty_node
                else ""
            )
            for link in row.select("td.column2 a[href]"):
                award = _normalise(link.get_text(" ", strip=True))
                if award.upper() not in MASTER_AWARDS:
                    continue
                source_url = urljoin(CATALOG_URL, str(link["href"]))
                slug = urlsplit(source_url).path.rstrip("/").rsplit("/", 1)[-1].lower()
                programme_id = f"uiuc-{slug}"
                if base_name == "Computer Science" and award.upper() == "MS":
                    programme_id = EXISTING_COMPUTER_SCIENCE_ID
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=f"{base_name} {award}",
                    degree_type=award,
                    faculty=faculty,
                    department=faculty,
                    source_url=source_url,
                    application_url=source_url,
                    windows=[],
                    deadline_text=(
                        "Illinois' official graduate degree index confirms this "
                        "master's award. Application deadlines are maintained by "
                        "the individual programme; no exact date pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-graduate-index",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: (item.name, item.id))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Illinois' official graduate index contained "
                f"{len(result)} master's awards; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
