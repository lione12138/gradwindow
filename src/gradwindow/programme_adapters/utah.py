from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    DiscoveredCatalog,
    DiscoveredWindow,
    Fetcher,
    ParserZeroResultError,
)
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://gradschool.utah.edu/degree-programs-and-contacts/"
DIRECTORY_DATA_URL = f"{CATALOG_URL}directory_code.php"
APPLICATION_URL = "https://gradschool.utah.edu/future-students/admissions.php"
KAHLERT_APPLICATION_URL = (
    "https://www.cs.utah.edu/graduate/prospective-students/admissions/"
    "graduate-application/"
)
KAHLERT_DEADLINE_URL = (
    "https://www.cs.utah.edu/graduate/prospective-students/admissions/"
    "graduate-deadline-details/"
)
KAHLERT_PROGRAMMES = {"Computer Science MS", "Computing MS"}


class UtahAdapter(OfficialCatalogAdapter):
    university_id = "university-of-utah"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "utah"
    institution_name = "University of Utah"
    minimum_expected_programmes = 122
    window_watch_urls = (KAHLERT_DEADLINE_URL,)
    retrieval_method = "official-graduate-degree-directory"
    catalogue_limitation_reason = (
        "Utah's Graduate School directory identifies master's degrees and their "
        "official departmental pages. Each graduate programme sets its own "
        "requirements and deadlines, so no central exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 122) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(DIRECTORY_DATA_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "each graduate program sets its own application deadlines" not in guidance
            or "online application system" not in guidance
        ):
            raise ValueError("Utah's official graduate admission guide is missing")
        self._add_kahlert_windows(catalog, fetcher(KAHLERT_DEADLINE_URL))
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select(".c-grid-layout__cell"):
            heading = card.select_one("h3")
            degree_node = card.select_one("p.h6")
            if heading is None or degree_node is None:
                continue
            degree = normalise(degree_node.get_text(" ", strip=True))
            if "master" not in degree.casefold():
                continue
            link = heading.select_one("a[href]")
            if link is not None:
                name = normalise(link.get_text(" ", strip=True))
            else:
                for decoration in heading.select('[aria-hidden="true"], .sr-only'):
                    decoration.decompose()
                name = normalise(heading.get_text(" ", strip=True))
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree,
                    source_url=(
                        urljoin(CATALOG_URL, str(link["href"]))
                        if link is not None
                        else CATALOG_URL
                    ),
                )
            )
        return rows

    def _add_kahlert_windows(
        self, catalog: DiscoveredCatalog, deadline_html: str
    ) -> None:
        text = normalise(
            BeautifulSoup(deadline_html, "html.parser").get_text(" ", strip=True)
        )
        deadline = re.search(
            r"Applications?\s+for\s+Fall\s+2027\b.*?"
            r"between\s+September\s+and\s+December\s+15,?\s+2026\b",
            text,
            re.IGNORECASE,
        )
        if deadline is None:
            raise ParserZeroResultError(
                "Utah Kahlert Fall 2027 deadline source produced zero windows"
            )

        matched = 0
        for programme in catalog.programmes:
            if programme.name not in KAHLERT_PROGRAMMES:
                continue
            programme.application_url = KAHLERT_APPLICATION_URL
            programme.windows = [
                DiscoveredWindow(
                    round="Fall admissions deadline",
                    closes_at="2026-12-15",
                    opens_at=None,
                    intake="Fall 2027",
                    source_url=KAHLERT_DEADLINE_URL,
                    opens_at_basis="missing",
                )
            ]
            programme.deadline_text = (
                "Kahlert School's official Fall 2027 page gives an exact "
                "December 15, 2026 closing date but describes opening only as "
                "September. No exact opening day is inferred."
            )
            programme.parse_status = "incomplete"
            matched += 1
        if matched != len(KAHLERT_PROGRAMMES):
            raise ParserZeroResultError(
                "Utah catalogue did not contain both Kahlert master's programmes"
            )
