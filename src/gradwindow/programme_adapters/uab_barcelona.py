from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.uab.cat/sites/ContentServer/studies/graduate/university-master-s-degrees/by-areas-of-knowledge-1345666814830.html"
APPLICATION_URL = "https://www.uab.cat/sites/ContentServer/studies/graduate/university-master-s-degrees/application-for-admission-to-a-master-s-degree-1345666814858.html"

_PROGRAMME_PATH = "/official-master-s-degrees/general-information/"
_ADMISSION_PATH = "/official-master-s-degrees/admission/"


class UABBarcelonaAdapter:
    university_id = "universitat-autonoma-de-barcelona"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    catalogue_limitation_reason = (
        "UAB publishes programme-level admission pages rather than one shared "
        "master's application window; no common dates are inferred."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 130,
        maximum_expected_programmes: int = 155,
        minimum_expected_application_links: int = 85,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.minimum_expected_application_links = minimum_expected_application_links

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        application_links = _application_link_count(fetcher(APPLICATION_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"UAB catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        if application_links < self.minimum_expected_application_links:
            raise ValueError(
                f"UAB admission index contained only {application_links} programme links"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main, #main")
    if main is None:
        raise ValueError("UAB catalogue did not expose its main content")
    faculty = "Universitat Autònoma de Barcelona"
    programmes: dict[str, DiscoveredProgramme] = {}
    for node in main.select("h2, a[href]"):
        if node.name == "h2":
            heading = normalise(node.get_text(" ", strip=True))
            if heading and heading != "By areas of knowledge":
                faculty = heading
            continue
        source_url = urljoin(CATALOG_URL, str(node.get("href", "")))
        if _PROGRAMME_PATH not in source_url:
            continue
        name = re.sub(
            r"\s+New$", "", normalise(node.get_text(" ", strip=True)), flags=re.I
        )
        if not name:
            continue
        programme_id = f"uab-barcelona-{slug(name)}"
        programmes[name.casefold()] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="University Master",
            faculty=faculty,
            department=faculty,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in UAB's official university master's "
                "directory. Admission schedules are programme-level, so no "
                "shared exact window is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-masters-by-area-directory",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _application_link_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    title = normalise(soup.get_text(" ", strip=True))
    if "Application for admission to a master's degree" not in title:
        raise ValueError("UAB master's admission index was not found")
    return sum(
        _ADMISSION_PATH in urljoin(APPLICATION_URL, str(link.get("href", "")))
        for link in soup.select("main a[href], #main a[href]")
    )
