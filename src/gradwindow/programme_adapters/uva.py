from __future__ import annotations

import json
import re
import unicodedata

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "the-university-of-amsterdam"
CATALOG_URL = "https://www.uva.nl/en/education/master-s/master-s-programmes/masters-programmes.html"
API_URL = "https://www.uva.nl/_restapi/list-json?uuid=8b5965c1-f8b3-43d2-b10c-9164cf4dbaca&mount=68e8cf3b-f553-4c29-beb6-54aa36d13f73"
APPLICATION_URL = "https://www.uva.nl/en/education/admissions/masters/applying-for-a-degree-programme.html"


class UvAAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 260) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        application_text = fetcher(APPLICATION_URL)
        if (
            "Every programme has its own" not in application_text
            and "Every programme" not in application_text
        ):
            raise ValueError(
                "UvA programme-specific application policy was unavailable"
            )
        return self.parse_json(fetcher(API_URL))

    def parse_json(self, payload: str) -> DiscoveredCatalog:
        data = json.loads(payload)
        programmes = {}
        for item in data.get("items", []):
            if item.get("studyType") != "master" and "masters" not in item.get(
                "programmeType", []
            ):
                continue
            name = str(item.get("title", "")).strip()
            source_url = str(item.get("url", "")).split("?", 1)[0]
            if not name or not source_url:
                continue
            faculty_values = item.get("faculty") or []
            faculty = " | ".join(
                str(value).replace("-", " ").title() for value in faculty_values
            )
            programme_id = f"uva-{_slug(name)}-master"
            if name == "Computer Science (joint degree UvA/VU)":
                programme_id = "uva-vu-computer-science-msc"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=_degree_type(item),
                faculty=faculty or "University of Amsterdam",
                department=faculty or "University of Amsterdam",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text="UvA publishes programme-specific application procedures and deadlines, but no exact universal opening date is provided. No date is inferred.",
                parse_status="no-deadline",
                retrieval_method="official-programme-json",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UvA catalogue contained {len(result)} master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _degree_type(item: dict) -> str:
    titles = item.get("studytitle") or []
    return str(titles[0]).upper() if titles else "Master"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
