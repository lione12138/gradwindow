from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

HEALTH_CATALOG_URL = (
    "https://www.utsouthwestern.edu/education/school-of-health-professions/programs/"
)
HEALTH_ADMISSIONS_URL = (
    "https://www.utsouthwestern.edu/education/school-of-health-professions/admissions/"
)
PUBLIC_HEALTH_CATALOG_URL = "https://osph.utsouthwestern.edu/degree-programs/"
PUBLIC_HEALTH_ADMISSIONS_URL = "https://osph.utsouthwestern.edu/admissions/"


class UTSWAdapter(BaseProgrammeAdapter):
    university_id = "university-of-texas-southwestern-medical-center"
    catalog_url = HEALTH_CATALOG_URL
    application_url = HEALTH_ADMISSIONS_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (
        HEALTH_CATALOG_URL,
        HEALTH_ADMISSIONS_URL,
        PUBLIC_HEALTH_CATALOG_URL,
        PUBLIC_HEALTH_ADMISSIONS_URL,
    )
    retrieval_method = "official-health-professions-and-public-health-catalogues"
    catalogue_limitation_reason = (
        "UT Southwestern publishes programme-specific admissions tables. The "
        "central pages provide many closing deadlines but not complete exact "
        "opening-and-closing pairs with years for every master's programme."
    )

    def __init__(self, minimum_expected_programmes: int = 8) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        rows = self._programmes(
            fetcher(HEALTH_CATALOG_URL),
            base_url=HEALTH_CATALOG_URL,
            faculty="School of Health Professions",
            application_url=HEALTH_ADMISSIONS_URL,
        )
        rows.extend(
            self._programmes(
                fetcher(PUBLIC_HEALTH_CATALOG_URL),
                base_url=PUBLIC_HEALTH_CATALOG_URL,
                faculty="Peter O'Donnell Jr. School of Public Health",
                application_url=PUBLIC_HEALTH_ADMISSIONS_URL,
            )
        )
        health_policy = normalise(
            BeautifulSoup(fetcher(HEALTH_ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        public_policy = normalise(
            BeautifulSoup(
                fetcher(PUBLIC_HEALTH_ADMISSIONS_URL), "html.parser"
            ).get_text(" ", strip=True)
        ).casefold()
        if (
            "deadlines" not in health_policy
            or "application deadlines" not in public_policy
        ):
            raise ValueError("UT Southwestern's admissions deadline tables are missing")
        deduplicated = {row.id: row for row in rows}
        result = sorted(deduplicated.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UT Southwestern catalogue contained {len(result)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)

    def _programmes(
        self,
        html: str,
        *,
        base_url: str,
        faculty: str,
        application_url: str,
    ) -> list[DiscoveredProgramme]:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select("main a[href]"):
            name = normalise(link.get_text(" ", strip=True))
            if not re.search(r"\bMaster\b", name, re.IGNORECASE):
                continue
            source_url = urljoin(base_url, link["href"])
            programme_id = f"utsw-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=application_url,
                windows=[],
                deadline_text=(
                    "Programme found on an official UT Southwestern school "
                    "catalogue. Admissions are programme-specific and the central "
                    "tables do not provide a complete exact opening-and-closing "
                    "pair with years, so no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        return list(programmes.values())
