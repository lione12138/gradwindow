from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredWindow, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://adm-g.postech.ac.kr/ENG/"
APPLICATION_URL = "https://adm-g.postech.ac.kr/ENG/application01/"
DATE_RANGE_RE = re.compile(
    r"(20\d{2}-\d{2}-\d{2})(?:\([A-Z]+\))?\s*~\s*"
    r"(20\d{2}-\d{2}-\d{2})"
)


class POSTECHAdapter(OfficialCatalogAdapter):
    university_id = "pohang-university-of-science-and-technology-postech"
    school_prefix = "postech"
    institution_name = "Pohang University of Science and Technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 17
    retrieval_method = "official-international-graduate-admissions"
    application_opens_at_basis = "official"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries = self.extract_entries(fetcher(CATALOG_URL))
        windows = self.extract_windows(fetcher(APPLICATION_URL))
        catalog = self._catalog(entries)
        for programme in catalog.programmes:
            programme.windows = [
                DiscoveredWindow(
                    round=window.round,
                    opens_at=window.opens_at,
                    closes_at=window.closes_at,
                    intake=window.intake,
                    applicant_categories=list(window.applicant_categories),
                    source_url=window.source_url,
                )
                for window in windows
            ]
            programme.deadline_text = (
                "Exact international graduate application periods published "
                "in POSTECH's official application table."
            )
            programme.parse_status = "exact"
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        programme_box = next(
            (
                box
                for box in soup.select("div.select_form")
                if "ACADEMIC PROGRAM" in box.get_text(" ", strip=True)
            ),
            None,
        )
        if programme_box is None:
            return []
        return [
            entry(
                name=anchor.get_text(" ", strip=True).title(),
                degree_type="MS",
                source_url=str(anchor["href"]),
                base_url=CATALOG_URL,
            )
            for anchor in programme_box.select("a[href]")
            if anchor.get_text(" ", strip=True)
        ]

    def extract_windows(self, html: str) -> list[DiscoveredWindow]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[tuple[str, DiscoveredWindow]] = []
        for row in soup.select("table tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
            if len(cells) < 4 or "International Application" not in cells[1]:
                continue
            match = DATE_RANGE_RE.search(cells[3])
            if match is None:
                continue
            rows.append(
                (
                    cells[0],
                    DiscoveredWindow(
                        round=cells[1],
                        opens_at=match.group(1),
                        closes_at=match.group(2),
                        intake=cells[0],
                        applicant_categories=["international-students"],
                        source_url=APPLICATION_URL,
                    ),
                )
            )
        if not rows:
            raise ValueError(
                "POSTECH application table had no exact international rows"
            )
        latest_cycle = max(cycle for cycle, _ in rows)
        return [window for cycle, window in rows if cycle == latest_cycle]
