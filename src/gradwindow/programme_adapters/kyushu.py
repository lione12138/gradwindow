from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.isc.kyushu-u.ac.jp/graduate/"
APPLICATION_URL = "https://isc.kyushu-u.ac.jp/invitation/"


class KyushuAdapter(BaseProgrammeAdapter):
    university_id = "kyushu-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 35

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.p-list__table")
        if table is None:
            raise ValueError(
                "Kyushu's official international programme table is missing"
            )

        faculty = "Kyushu University"
        faculty_url = CATALOG_URL
        programmes: dict[str, DiscoveredProgramme] = {}
        for row in table.select("tr"):
            cells = row.find_all("td")
            if len(cells) >= 3:
                faculty = normalise(cells[0].get_text(" ", strip=True))
                faculty_link = cells[0].select_one("a[href]")
                faculty_url = (
                    urljoin(CATALOG_URL, str(faculty_link.get("href", "")))
                    if faculty_link is not None
                    else CATALOG_URL
                )
                programme_cell, degree_cell = cells[1], cells[2]
            elif len(cells) == 2:
                programme_cell, degree_cell = cells
            else:
                continue

            offered = normalise(degree_cell.get_text(" ", strip=True)).upper()
            if re.search(r"(?:^|/)M(?:/|$)", offered) is None:
                continue
            name = normalise(programme_cell.get_text(" ", strip=True))
            if not name:
                continue
            programme_link = programme_cell.select_one("a[href]")
            source_url = (
                urljoin(CATALOG_URL, str(programme_link.get("href", "")))
                if programme_link is not None
                else faculty_url
            )
            programme_id = f"kyushu-international-{slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="LLM" if "LL.M" in name.upper() else "Master",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Kyushu's official English-taught programme table confirms this "
                    "master's route. Admission schedules are maintained by the "
                    "individual graduate schools, and the central page does not give "
                    "a complete exact opening-and-closing pair, so no dates are "
                    "inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-english-graduate-programme-table",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Kyushu's official table contained "
                f"{len(result)} English-taught master's programmes; expected at "
                f"least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
