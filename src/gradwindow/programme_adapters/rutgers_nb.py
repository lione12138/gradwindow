from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://grad.admissions.rutgers.edu/GraduateProgram/"
APPLICATION_URL = "https://grad.admissions.rutgers.edu/"
_PROGRAMME_RE = re.compile(
    r"^(?P<name>.+?)\s+\((?P<degree>[^()]+)\)\s*-?\s*New Brunswick$"
)


class RutgersNBAdapter:
    university_id = "rutgers-university-new-brunswick"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    catalogue_limitation_reason = (
        "Rutgers–New Brunswick directs applicants to each programme's "
        "Requirements and Deadlines page. Those official detail pages remain "
        "programme-level watch sources and no common exact window is inferred."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 140,
        maximum_expected_programmes: int = 165,
        *,
        search_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.search_fetcher = search_fetcher or _fetch_filtered_search

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        landing = fetcher(CATALOG_URL)
        if "Requirements and Deadlines" not in normalise(
            BeautifulSoup(landing, "html.parser").get_text(" ", strip=True)
        ):
            raise ValueError("Rutgers graduate programme search guidance is missing")
        programmes = _programmes(self.search_fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Rutgers–New Brunswick search returned {len(programmes)} "
                f"master's programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    count_text = normalise(soup.get_text(" ", strip=True))
    if re.search(r"\d+\s+Programs?\(s\)", count_text) is None:
        raise ValueError("Rutgers filtered programme count is missing")
    programmes: dict[str, DiscoveredProgramme] = {}
    for table_row in soup.select("table tr"):
        cells = table_row.find_all("td")
        detail = table_row.select_one("a[href*='Detail.aspx']")
        if len(cells) < 3 or detail is None:
            continue
        label = normalise(cells[0].get_text(" ", strip=True))
        match = _PROGRAMME_RE.match(label)
        if match is None:
            continue
        name = normalise(match.group("name"))
        degree = normalise(match.group("degree"))
        area = normalise(cells[1].get_text(" ", strip=True)) or "Rutgers–New Brunswick"
        source_url = urljoin(CATALOG_URL, str(detail["href"]))
        programme_id = f"rutgers-nb-{slug(name)}-{slug(degree)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type=degree,
            faculty="Rutgers–New Brunswick",
            department=area,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Rutgers' official search lists this New Brunswick master's "
                "programme and links to its programme-specific Requirements "
                "and Deadlines page. No common exact window is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-filtered-graduate-programme-search",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _fetch_filtered_search(url: str) -> str:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    with httpx.Client(follow_redirects=True, timeout=90, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        payload = {
            field.get("name"): field.get("value", "")
            for field in soup.select("form input[type='hidden'][name]")
        }
        payload.update(
            {
                "ctl00$ContentPlaceHolder1$ResultsPerPage": "0",
                "ctl00$ContentPlaceHolder1$AppTypeList": "Degree",
                "ctl00$ContentPlaceHolder1$TypeList": "Masters",
                "ctl00$ContentPlaceHolder1$CurriculumList": "",
                "ctl00$ContentPlaceHolder1$CampusList": "New Brunswick",
                "ctl00$ContentPlaceHolder1$SearchButton": "Search",
            }
        )
        response = client.post(url, data=payload)
        response.raise_for_status()
        return response.text
