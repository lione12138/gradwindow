from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://gradapp.ucsf.edu/portal/app-selection-portal?tab=masters"
TABLE_URL = (
    "https://gradapp.ucsf.edu/portal/data/table?"
    "portal_id=dac955c9-a7fc-4a0c-a21c-30350a083815&"
    "part=ca49a15a-8942-4f42-a31a-4c3dcb6f2515"
)
APPLICATION_URL = "https://gradapp.ucsf.edu/apply/"
MASTER_LEVELS = {"MA", "MAS", "MEPN", "MHA", "MPH", "MS"}


class UCSFAdapter(BaseProgrammeAdapter):
    university_id = "university-of-california-san-francisco"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, TABLE_URL)
    retrieval_method = "official-slate-masters-table"

    def __init__(self, minimum_expected_programmes: int = 12) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        # The public portal loads this first-party Slate table lazily.
        return self.parse_catalog(fetcher(TABLE_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for row in soup.select("tbody tr"):
            cells = [
                normalise(cell.get_text(" ", strip=True)) for cell in row.select("td")
            ]
            if len(cells) < 2 or cells[1].upper() not in MASTER_LEVELS:
                continue
            name, level = cells[:2]
            if not name:
                continue
            opening_text = cells[2] if len(cells) > 2 else ""
            closing_text = cells[3] if len(cells) > 3 else ""
            deadline_text = (
                "Programme is listed in UCSF's official master's application table."
            )
            if opening_text or closing_text:
                deadline_text += (
                    f" The table currently shows opening date {opening_text or 'not listed'}"
                    f" and closing date {closing_text or 'not listed'}. No exact window"
                    " is created unless both dates are official."
                )
            programme_id = f"ucsf-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=level,
                faculty="UCSF Graduate Division",
                department="UCSF Graduate Division",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=deadline_text,
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UCSF portal contained {len(result)} master's routes; expected at "
                f"least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
