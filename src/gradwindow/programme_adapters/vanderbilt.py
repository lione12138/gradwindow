from __future__ import annotations

import html
from collections.abc import Callable

import httpx
from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://gradschool.vanderbilt.edu/academics/programs-departments/"
PROGRAM_API_URL = "https://web.dev-api.vanderbilt.edu/program-finder"
ADMISSIONS_URL = "https://gradschool.vanderbilt.edu/admissions/apply/"

ApiFetcher = Callable[[str], object]


class VanderbiltAdapter(BaseProgrammeAdapter):
    university_id = "vanderbilt-university"
    catalog_url = CATALOG_URL
    admissions_url = ADMISSIONS_URL
    application_url = ADMISSIONS_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-program-finder-api"
    catalogue_limitation_reason = (
        "Vanderbilt states that applications open August 1 and deadlines vary by "
        "programme, but the statement has no cycle year and is not a complete exact "
        "programme window. Programme requirements remain monitored."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 65,
        api_fetcher: ApiFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.api_fetcher = api_fetcher or _fetch_program_api

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        if PROGRAM_API_URL not in wrapper:
            raise ValueError("Vanderbilt's official programme finder API is missing")
        policy = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "applications open august 1st" not in policy or (
            "deadlines vary by program" not in policy
        ):
            raise ValueError(
                "Vanderbilt's programme-specific deadline policy is missing"
            )
        return self.parse_api_payload(self.api_fetcher(PROGRAM_API_URL))

    def parse_api_payload(self, payload: object) -> DiscoveredCatalog:
        if not isinstance(payload, list):
            raise ValueError("Vanderbilt programme finder did not return a list")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in payload:
            if not isinstance(item, dict) or not item.get("masters"):
                continue
            name = normalise(html.unescape(str(item.get("program", ""))))
            source_url = str(item.get("masters", "")).strip()
            if not name or not source_url.startswith("https://"):
                continue
            schools = item.get("schoollist", [])
            faculty = (
                "; ".join(normalise(str(value)) for value in schools if value)
                if isinstance(schools, list)
                else "Vanderbilt University"
            )
            faculty = faculty or "Vanderbilt University"
            degree_type = normalise(str(item.get("masters_type", ""))) or "Master"
            source_id = str(item.get("program_id", "")).strip()
            programme_id = f"vanderbilt-{source_id or slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=ADMISSIONS_URL,
                windows=[],
                deadline_text=(
                    "Programme found through Vanderbilt's official programme finder. "
                    "The university says deadlines vary by programme and its August "
                    "opening statement has no cycle year, so no exact date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Vanderbilt programme finder contained {len(result)} master's "
                f"routes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _fetch_program_api(url: str) -> object:
    headers = {
        "Accept": "application/json",
        "Origin": "https://gradschool.vanderbilt.edu",
        "Referer": CATALOG_URL,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140 Safari/537.36"
        ),
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
