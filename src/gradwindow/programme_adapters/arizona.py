from __future__ import annotations

import json
import re
from collections.abc import Callable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://grad.arizona.edu/admissions-guides/"
DEADLINES_URL = "https://grad.arizona.edu/admissions/procedures/application-deadlines"
APPLICATION_URL = "https://apply.grad.arizona.edu/"
DETAIL_URL = "https://grad.arizona.edu/admissions-guides/program/{}"

_API_CONFIG_RE = re.compile(
    r'fetch\("(?P<endpoint>https://[^"\s]+execute-api[^"\s]+)".*?'
    r'"X-API-Key":"(?P<key>[^"]+)"',
    re.DOTALL,
)

_QUERY = """query AdmissionsGuides {
  admissionsGuides {
    uacadPlan
    acadPlanType
    displayName
    degreeName
    degreeType
    lastAdmitTerm
    acadCareer
    admissionsDeadlines
    planCampuses { campus campusDescr locationDescr }
    planOwners { academicUnit websiteUrl college }
  }
}"""


class ArizonaAdapter:
    university_id = "university-of-arizona"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, DEADLINES_URL)
    retrieval_method = "official-graduate-admissions-graphql"
    catalogue_limitation_reason = (
        "The University of Arizona delegates deadlines to each programme. The "
        "official directory exposes programme-specific deadline text, usually "
        "without cycle years or exact opening dates, so those policies remain "
        "review guidance and no complete exact window is inferred."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 300,
        maximum_expected_programmes: int = 360,
        *,
        api_fetcher: Callable[[str, str], str] | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.api_fetcher = api_fetcher or _fetch_api

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog_html = fetcher(CATALOG_URL)
        script_url = _application_script_url(catalog_html)
        endpoint, api_key = _api_config(fetcher(script_url))
        policy = normalise(
            BeautifulSoup(fetcher(DEADLINES_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "does not have specific application deadlines" not in policy:
            raise ValueError("Arizona's programme-specific deadline policy is missing")
        programmes = _programmes(self.api_fetcher(endpoint, api_key))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Arizona directory contained {len(programmes)} active master's "
                f"plans; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _application_script_url(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select("script[src]"):
        source = str(script.get("src", ""))
        if "admissions-guides" in source and source.endswith(".js"):
            return urljoin(CATALOG_URL, source)
    raise ValueError("Arizona admissions guide did not expose its application script")


def _api_config(script: str) -> tuple[str, str]:
    match = _API_CONFIG_RE.search(script)
    if match is None:
        raise ValueError("Arizona application script did not expose its public API")
    return match.group("endpoint"), match.group("key")


def _fetch_api(endpoint: str, api_key: str) -> str:
    response = httpx.post(
        endpoint,
        headers={
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-API-Key": api_key,
        },
        json={"query": _QUERY},
        timeout=90,
    )
    response.raise_for_status()
    return response.text


def _programmes(payload: str) -> list[DiscoveredProgramme]:
    try:
        rows = json.loads(payload)["data"]["admissionsGuides"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Arizona API did not return admissions guides") from exc
    programmes: dict[str, DiscoveredProgramme] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if (
            row.get("degreeType") != "Masters"
            or row.get("acadCareer") != "GRAD"
            or row.get("acadPlanType") != "MAJ"
            or normalise(row.get("lastAdmitTerm") or "")
        ):
            continue
        plan = normalise(row.get("uacadPlan") or "")
        name = normalise(row.get("displayName") or "")
        degree = normalise(row.get("degreeName") or "") or "Master"
        if not plan or not name:
            continue
        owners = row.get("planOwners") or []
        faculty = normalise(
            next(
                (
                    owner.get("college")
                    for owner in owners
                    if isinstance(owner, dict) and owner.get("college")
                ),
                "University of Arizona",
            )
        )
        department = normalise(
            next(
                (
                    owner.get("academicUnit")
                    for owner in owners
                    if isinstance(owner, dict) and owner.get("academicUnit")
                ),
                faculty,
            )
        )
        deadline = normalise(
            BeautifulSoup(
                str(row.get("admissionsDeadlines") or ""), "html.parser"
            ).get_text(" ", strip=True)
        )
        source_url = DETAIL_URL.format(plan)
        programme_id = f"arizona-{slug(plan)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type=degree,
            faculty=faculty,
            department=department,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                f"Official programme deadline guidance: {deadline[:1600]}"
                if deadline
                else (
                    "The official Arizona programme guide currently publishes "
                    "no admissions deadline text for this active master's plan."
                )
            ),
            parse_status="no-deadline",
            retrieval_method="official-graduate-admissions-graphql",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())
