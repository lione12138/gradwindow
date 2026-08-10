from __future__ import annotations

import re
from datetime import date, datetime, timezone

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredWindow, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    normalise,
)

CATALOG_URL = "https://grad.uci.edu/admissions/degree-programs/"
RESULTS_URL = "https://apply.grad.uci.edu/portal/degree_program?cmd=getresults"
APPLICATION_URL = "https://apply.grad.uci.edu/apply/"
DATE_RE = re.compile(r"Application Deadline:\s*([A-Z][a-z]+\s+\d{1,2},\s+20\d{2})")


class UCIAdapter(OfficialCatalogAdapter):
    university_id = "university-of-california-irvine"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "uci"
    institution_name = "University of California, Irvine"
    minimum_expected_programmes = 70
    window_watch_urls = (RESULTS_URL,)
    retrieval_method = "official-graduate-division-programme-portal"
    catalogue_limitation_reason = (
        "UCI's official portal publishes programme closing dates but not exact "
        "opening dates. Current closing dates are retained as review guidance only."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 70,
        reference_date: date | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.reference_date = reference_date or datetime.now(timezone.utc).date()

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        shell = fetcher(CATALOG_URL)
        if "degree_program" not in shell:
            raise ValueError("UCI's official degree-program portal embed is missing")
        soup = BeautifulSoup(fetcher(RESULTS_URL), "html.parser")
        entries = []
        deadlines: dict[str, str] = {}
        for card in soup.select(".card"):
            title = card.select_one(".card-title")
            badges = [
                normalise(item.get_text(" ", strip=True))
                for item in card.select(".degree_button")
            ]
            if title is None or "Master's" not in badges:
                continue
            name = normalise(next(title.stripped_strings, ""))
            details = card.select_one(".details-cell a[href]")
            if not name or details is None:
                continue
            source_url = str(details["href"])
            entries.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=source_url,
                )
            )
            text = normalise(card.get_text(" ", strip=True))
            match = DATE_RE.search(text)
            if match:
                closes_at = datetime.strptime(match.group(1), "%B %d, %Y").date()
                if closes_at >= self.reference_date:
                    deadlines[source_url] = match.group(1)
        catalog = self._catalog(entries)
        for programme in catalog.programmes:
            deadline = deadlines.get(programme.source_url)
            if deadline:
                closes_at = datetime.strptime(deadline, "%B %d, %Y").date()
                programme.windows = [
                    DiscoveredWindow(
                        round="Official programme deadline",
                        closes_at=closes_at.isoformat(),
                        intake="Varies by programme",
                        source_url=RESULTS_URL,
                    )
                ]
                programme.deadline_text = (
                    f"Official UCI programme deadline: {deadline}. "
                    "The portal does not publish an exact opening date."
                )
                programme.parse_status = "incomplete"
        return catalog
