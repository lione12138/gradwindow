from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://www.studium.uni-mainz.de/en/wp-json/"
    "jgu-study-finder/v1/courses-of-study?lang=en"
)
APPLICATION_URL = (
    "https://www.studium.uni-mainz.de/en/your-application/masters-degrees/"
)


class MainzAdapter:
    university_id = "johannes-gutenberg-university-mainz"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    known_programme_window_scope_type = "programme-group"
    catalogue_limitation_reason = (
        "JGU's official API enumerates master's programmes. Its exact summer "
        "2027 periods differ by restricted and unrestricted routes; other "
        "cycles and programme exceptions remain route-specific."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 125,
        maximum_expected_programmes: int = 145,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Mainz API contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        _validate_dates(fetcher(APPLICATION_URL))
        programmes.extend(_admission_groups())
        return DiscoveredCatalog(
            application_opens_at="2026-11-09",
            programmes=programmes,
        )


def _programmes(payload: str) -> list[DiscoveredProgramme]:
    records = json.loads(payload)
    if not isinstance(records, list):
        raise ValueError("Mainz course API did not return a list")
    programmes: dict[str, DiscoveredProgramme] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        degree = normalise(record.get("degree", ""))
        if not degree.startswith(("Master", "Magister")):
            continue
        api_id = slug(record.get("id", ""))
        name = normalise(record.get("fieldOfStudy", ""))
        source_url = normalise(record.get("zulassungsv_link", ""))
        faculty = normalise(record.get("faechergruppen", "")) or "JGU Mainz"
        if not api_id or not name or not source_url.startswith("http"):
            continue
        programme_id = f"mainz-{api_id}-{slug(degree)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type=degree,
            faculty=faculty,
            department=faculty,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme found in Johannes Gutenberg University Mainz's "
                "official course API. Shared summer routes are represented at "
                "programme-group scope; programme exceptions are not inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-study-finder-json-api",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _validate_dates(html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    required = (
        r"summer semester 2027",
        r"November 09, 2026 to December 04, 2026",
        r"November 09, 2026 to March 01, 2027",
    )
    if not all(re.search(pattern, text, re.I) for pattern in required):
        raise ValueError("Mainz's official guide lacked its exact summer 2027 routes")


def _admission_groups() -> list[DiscoveredProgramme]:
    definitions = (
        (
            "mainz-summer-2027-restricted-master-admissions",
            "Summer 2027 restricted master's admissions",
            "Restricted admission (including aptitude test or interview)",
            "2026-12-04",
        ),
        (
            "mainz-summer-2027-unrestricted-master-admissions",
            "Summer 2027 unrestricted master's admissions",
            "Without admission restrictions",
            "2027-03-01",
        ),
    )
    return [
        DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty="Student Services",
            department="Student Services",
            source_url=APPLICATION_URL,
            application_url=APPLICATION_URL,
            windows=[
                DiscoveredWindow(
                    round=round_name,
                    applicant_categories=["all"],
                    opens_at="2026-11-09",
                    closes_at=closes_at,
                    intake="Summer 2027",
                    source_url=APPLICATION_URL,
                    opens_at_basis="official",
                )
            ],
            deadline_text=(
                "JGU Mainz's official master's application guide publishes "
                "this one-time exact Summer 2027 route."
            ),
            parse_status="parsed",
            retrieval_method="official-master-application-guide-html",
            evidence_quality="official-full-text",
        )
        for programme_id, name, round_name, closes_at in definitions
    ]
