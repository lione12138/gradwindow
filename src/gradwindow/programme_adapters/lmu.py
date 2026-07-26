from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme

UNIVERSITY_ID = "ludwig-maximilians-universit-t-m-nchen"
CATALOG_URL = (
    "https://www.lmu.de/en/study/all-degrees-and-programs/"
    "international-degree-programs/"
)
APPLICATION_URL = (
    "https://www.lmu.de/en/study/degree-students/applications-for-admission/"
)
EXISTING_STATISTICS_ID = "lmu-statistics-data-science-msc"


class LMUAdapter(BaseProgrammeAdapter):
    """Discover LMU's centrally listed English-taught master's programmes."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 35) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        section = next(
            (
                heading.parent
                for heading in soup.find_all(["h2", "h3"])
                if "english-taught master's degree programs"
                in _normalise(heading.get_text(" ", strip=True)).lower()
            ),
            None,
        )
        programmes: dict[str, DiscoveredProgramme] = {}
        if section is not None:
            for link in section.find_all("a", href=True):
                title = _normalise(link.get_text(" ", strip=True))
                if not title:
                    continue
                programme_id = f"lmu-{_slug(title)}-master"
                degree_type = _degree_type(title)
                name = f"Master's Programme in {title}"
                if title == "Statistics and Data Science":
                    programme_id = EXISTING_STATISTICS_ID
                    degree_type = "MSc"
                    name = "MSc Statistics and Data Science"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree_type,
                    faculty="LMU Munich",
                    department="LMU Munich",
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "LMU lists this English-taught master's programme centrally, "
                        "but admission procedures and dates are programme-specific. "
                        "No exact opening-and-closing pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-english-masters-directory-html",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"LMU's official directory contained {len(result)} English-taught "
                f"master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _degree_type(title: str) -> str:
    if "LL.M" in title.upper():
        return "LLM"
    if "MBA" in title.upper():
        return "MBA"
    return "Master"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
