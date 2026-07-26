from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme

UNIVERSITY_ID = "kyoto-university"
CATALOG_URL = (
    "https://www.kyoto-u.ac.jp/en/education-campus/education-and-admissions/"
    "english-taught-degree-programs"
)
APPLICATION_URL = (
    "https://www.kyoto-u.ac.jp/en/education-campus/education-and-admissions/"
    "graduate-degree-programs"
)


class KyotoAdapter(BaseProgrammeAdapter):
    """Discover Kyoto University's centrally listed English-taught masters."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)

    def __init__(self, minimum_expected_programmes: int = 12) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        in_graduate_section = False
        faculty = "Kyoto University"
        programmes: dict[str, DiscoveredProgramme] = {}
        for node in soup.find_all(["h2", "h3", "h4"]):
            heading = _normalise(node.get_text(" ", strip=True))
            if node.name == "h2":
                if heading.lower() == "graduate programs":
                    in_graduate_section = True
                    continue
                if in_graduate_section:
                    break
            if not in_graduate_section:
                continue
            if node.name == "h3":
                faculty = heading
                continue
            if node.name != "h4":
                continue
            table = node.find_next_sibling("table")
            if (
                table is None
                or "master's" not in _normalise(table.get_text(" ", strip=True)).lower()
            ):
                continue
            link = node.find("a", href=True)
            source_link = str(link.get("href", "")) if link is not None else ""
            name = heading
            programme_id = f"kyoto-{_slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=_degree_type(name),
                faculty=faculty,
                department=faculty,
                source_url=CATALOG_URL,
                application_url=source_link or APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Kyoto University identifies this as an English-taught master's "
                    "programme. The central table gives intake and guideline "
                    "publication months, not an exact application opening-and-closing "
                    "pair, so no dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-english-degree-directory-html",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Kyoto University's official directory contained {len(result)} "
                f"English-taught master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _degree_type(name: str) -> str:
    upper = name.upper()
    if "MBA" in upper:
        return "MBA"
    if "MASTER OF ARTS" in upper:
        return "MA"
    return "Master"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
