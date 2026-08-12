from __future__ import annotations

import hashlib
import json

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://exdd-academics.webapps.iu.edu/api/public/v1/endpoint/degrees?campus=Bloomington&program_type=7&perPage=500"
APPLICATION_URL = "https://graduate.indiana.edu/apply/how-to-apply/index.html"


class IndianaBloomingtonAdapter:
    university_id = "indiana-university-bloomington"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    catalogue_limitation_reason = (
        "Indiana University Bloomington explicitly assigns application "
        "deadlines to departments; the central catalogue has no shared window."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 330,
        maximum_expected_programmes: int = 370,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        _verify_deadline_policy(fetcher(APPLICATION_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Indiana Bloomington catalogue contained {len(programmes)} "
                f"master's offerings; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(payload: str) -> list[DiscoveredProgramme]:
    try:
        data = json.loads(payload)["data"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("Indiana catalogue API did not return readable JSON") from exc
    if not isinstance(data, list):
        raise ValueError("Indiana catalogue API data was not a list")

    programmes: dict[str, DiscoveredProgramme] = {}
    for item in data:
        if not isinstance(item, dict) or item.get("diploma_badge") != "Master's":
            continue
        if item.get("campus") != "IU Bloomington":
            continue
        name = normalise(item.get("name", ""))
        degree = normalise(item.get("degree", ""))
        source_url = str(item.get("url", "")).strip()
        schools = item.get("schools") or []
        faculty = " | ".join(
            normalise(school.get("name", ""))
            for school in schools
            if isinstance(school, dict) and school.get("name")
        )
        if not name or not degree or not source_url:
            continue
        identity = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:8]
        programme_id = f"indiana-{slug(name)}-{slug(degree)}-{identity}"
        programmes[source_url] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type=degree,
            faculty=faculty or "Indiana University Bloomington",
            department=faculty or "Indiana University Bloomington",
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Offering is returned by Indiana University's official public "
                "Bloomington master's API. The Graduate School states that "
                "departments set their own deadlines, so none is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-public-academic-degrees-api",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _verify_deadline_policy(html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if "Departments set their own application deadlines" not in text:
        raise ValueError("Indiana's department-specific deadline policy changed")
