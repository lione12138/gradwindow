from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "king-fahd-university-of-petroleum-and-minerals"
CATALOG_URL = "https://bulletin.kfupm.edu.sa/programs/graduate-programs/"
PROJECT_CATALOG_URL = "https://ms.kfupm.edu.sa/"
APPLICATION_URL = "https://cgis.kfupm.edu.sa/applyy/apply-website"
EXISTING_DATA_SCIENCE_ID = "kfupm-data-science-analytics-ms"


class KFUPMAdapter(BaseProgrammeAdapter):
    """Combine KFUPM's official thesis and project master's catalogues."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL, PROJECT_CATALOG_URL)

    def __init__(self, minimum_expected_programmes: int = 65) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        return self.parse_pages(fetcher(CATALOG_URL), fetcher(PROJECT_CATALOG_URL))

    def parse_pages(self, thesis_html: str, project_html: str) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        canonical_names: set[str] = set()
        thesis = BeautifulSoup(thesis_html, "html.parser")
        for link in thesis.find_all("a", href=True):
            name = _normalise(link.get_text(" ", strip=True))
            if not _is_master(name):
                continue
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            programme = _programme(name, source_url, "official-graduate-bulletin-html")
            programmes[programme.id] = programme
            canonical_names.add(_canonical_name(name))
        project = BeautifulSoup(project_html, "html.parser")
        for heading in project.find_all("h2"):
            name = re.sub(
                r"^\s*\d+\.\s*", "", _normalise(heading.get_text(" ", strip=True))
            )
            status = re.search(
                r"\s+(?:\d+\s+YEARS?|HIVE\b|CLOSED\b|New\b)",
                name,
                flags=re.IGNORECASE,
            )
            if status:
                name = name[: status.start()].strip()
            if not _is_master(name):
                continue
            if _canonical_name(name) in canonical_names:
                continue
            programme = _programme(
                name, PROJECT_CATALOG_URL, "official-project-masters-page-html"
            )
            programmes[programme.id] = programme
            canonical_names.add(_canonical_name(name))
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"KFUPM's official catalogues contained {len(result)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _programme(name: str, source_url: str, method: str) -> DiscoveredProgramme:
    programme_id = f"kfupm-{_slug(name)}-master"
    if name == "Master of Science in Data Science & Analytics":
        programme_id = EXISTING_DATA_SCIENCE_ID
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type=_degree_type(name),
        faculty="King Fahd University of Petroleum & Minerals",
        department="King Fahd University of Petroleum & Minerals",
        source_url=source_url,
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text=(
            "KFUPM lists this master's programme in an official catalogue. "
            "Application cycles and availability can differ by programme; no exact "
            "opening-and-closing pair is inferred from catalogue status labels."
        ),
        parse_status="no-deadline",
        retrieval_method=method,
        evidence_quality="official-full-text",
    )


def _is_master(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("master") or lower.startswith("executive master")


def _canonical_name(value: str) -> str:
    return re.sub(r"\s*\((?:E?MBA)\)\s*$", "", value, flags=re.IGNORECASE).lower()


def _degree_type(value: str) -> str:
    lower = value.lower()
    if "executive master of business administration" in lower:
        return "EMBA"
    if "master of business administration" in lower:
        return "MBA"
    if "master of science" in lower:
        return "MSc"
    return "Master"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
