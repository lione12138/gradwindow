from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "lund-university"
CATALOG_URL = (
    "https://www.lunduniversity.lu.se/study/courses-programmes/%2A/educations/"
    "1/EducationsFilterByType-programme/"
)
APPLICATION_URL = "https://www.lunduniversity.lu.se/study/admission-degree-studies"
EXISTING_MACHINE_LEARNING_ID = "lund-machine-learning-systems-control-msc"


class LundAdapter(BaseProgrammeAdapter):
    """Discover every master's result in Lund's official programme search."""

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
        first_page = fetcher(CATALOG_URL)
        last_page = _last_page(first_page)
        pages = [first_page]
        pages.extend(fetcher(_page_url(page)) for page in range(2, last_page + 1))
        return self.parse_pages(pages)

    def parse_pages(self, pages: list[str]) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for hit in soup.select("li.hit--educations"):
                metadata = hit.select_one(".education-course-points")
                link = hit.select_one("h3 a[href]")
                if metadata is None or link is None:
                    continue
                if (
                    "master's programme"
                    not in _normalise(metadata.get_text(" ", strip=True)).lower()
                ):
                    continue
                name = _normalise(link.get_text(" ", strip=True))
                source_url = str(link.get("href", ""))
                code = _programme_code(source_url)
                programme_id = (
                    f"lund-{code.lower()}-{_slug(name)}-master"
                    if code
                    else f"lund-{_slug(name)}-master"
                )
                if name.startswith("Machine Learning, Systems and Control"):
                    programme_id = EXISTING_MACHINE_LEARNING_ID
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=_degree_type(name),
                    faculty="Lund University",
                    department="Lund University",
                    source_url=source_url,
                    application_url=source_url,
                    windows=[],
                    deadline_text=(
                        "Lund's official search identifies this as a master's "
                        "programme. Application rounds and dates are published on "
                        "the programme page and the national admissions service; no "
                        "exact opening-and-closing pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-programme-search-pagination",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Lund's official search contained {len(result)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _last_page(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = []
    for link in soup.find_all("a", href=True):
        match = re.search(r"/educations/(\d+)/", str(link.get("href", "")))
        if match:
            pages.append(int(match.group(1)))
    return max(pages, default=1)


def _page_url(page: int) -> str:
    return CATALOG_URL.replace("/educations/1/", f"/educations/{page}/")


def _programme_code(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    match = re.search(r"-([A-Z0-9]{4,8})$", path)
    return match.group(1) if match else ""


def _degree_type(name: str) -> str:
    lower = name.lower()
    if "master of science" in lower:
        return "MSc"
    if "master of arts" in lower:
        return "MA"
    return "Master"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
