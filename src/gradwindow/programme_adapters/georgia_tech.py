from __future__ import annotations

import json
from datetime import datetime

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://gradapp.gatech.edu/portal/program-info?cmd=get-programs"
APPLICATION_URL = "https://grad.gatech.edu/admissions"
DETAIL_URL = (
    "https://gradapp.gatech.edu/portal/program-info?cmd=view-program&program={}"
)
EXISTING_COMPUTER_SCIENCE_ID = "gatech-computer-science-ms"


class GeorgiaTechAdapter(BaseProgrammeAdapter):
    university_id = "georgia-institute-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 105

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        payload = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(payload)

    def parse_catalog(self, payload: str) -> DiscoveredCatalog:
        document = json.loads(payload)
        rows = document.get("row", [])
        if not isinstance(rows, list):
            raise ValueError("Georgia Tech programme portal returned invalid rows")

        programmes: dict[str, DiscoveredProgramme] = {}
        for row in rows:
            if not isinstance(row, dict) or row.get("level") != "Masters":
                continue
            name = normalise(str(row.get("name", "")))
            campus = normalise(str(row.get("campus", "")))
            guid = normalise(str(row.get("guid", "")))
            if not name or not campus or not guid:
                continue
            display_name = name if campus == "Atlanta" else f"{name} ({campus})"
            programme_id = f"gatech-{slug(name)}-{slug(campus)}-master"
            if name == "Computer Science" and campus == "Atlanta":
                programme_id = EXISTING_COMPUTER_SCIENCE_ID
            source_url = DETAIL_URL.format(guid)
            terms = {
                str(term.get("ayt_guid", "")): normalise(str(term.get("name", "")))
                for term in row.get("terms", [])
                if isinstance(term, dict)
            }
            windows = [
                DiscoveredWindow(
                    round="Application deadline",
                    intake=terms.get(str(deadline.get("ayt_guid", ""))) or None,
                    opens_at=None,
                    closes_at=_iso_date(str(deadline.get("date", ""))),
                    source_url=source_url,
                )
                for deadline in row.get("deadlines", [])
                if isinstance(deadline, dict) and deadline.get("date")
            ]
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=display_name,
                degree_type="Master",
                faculty=normalise(str(row.get("unit_college", "")))
                or "Georgia Institute of Technology",
                department=normalise(str(row.get("unit", "")))
                or "Georgia Institute of Technology",
                source_url=source_url,
                application_url=source_url,
                windows=windows,
                deadline_text=(
                    "The official Georgia Tech portal publishes exact closing "
                    "deadlines for this programme, but no exact opening date. "
                    "The incomplete windows remain unpublished and monitored."
                ),
                parse_status="incomplete" if windows else "no-deadline",
                retrieval_method="official-graduate-admissions-json",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Georgia Tech's official portal contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _iso_date(value: str) -> str:
    return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
