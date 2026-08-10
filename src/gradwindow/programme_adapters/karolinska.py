from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://education.ki.se/bachelors-masters-studies/programmes-and-courses"
ADMISSIONS_URL = (
    "https://education.ki.se/bachelors-masters-studies/apply/"
    "apply-for-a-masters-programme"
)
APPLICATION_URL = "https://www.universityadmissions.se/intl/start"
_WINDOW_RE = re.compile(
    r"Application period\s+(?P<opens>\d{1,2}\s+[A-Z][a-z]+\s+20\d{2})\s*"
    r"[-–—]\s*(?P<closes>\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}).{0,160}?"
    r"(?:autumn|fall)\s+(?P<intake_year>20\d{2})",
    re.IGNORECASE,
)


class KarolinskaAdapter(BaseProgrammeAdapter):
    university_id = "karolinska-institutet"
    catalog_url = CATALOG_URL
    admissions_url = ADMISSIONS_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2027"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-programme-catalogue-and-application-period"
    known_programme_window_scope_type = "institution"
    known_programme_window_scope_id = "karolinska-institutet"

    def __init__(self, minimum_expected_programmes: int = 10) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = self._programmes(fetcher(CATALOG_URL))
        opens_at, closes_at, intake = self._window(fetcher(ADMISSIONS_URL))
        programmes.append(
            DiscoveredProgramme(
                id="karolinska-international-masters-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="Karolinska Institutet",
                department="Central admissions",
                source_url=ADMISSIONS_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International master's application period",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=intake,
                        source_url=ADMISSIONS_URL,
                    )
                ],
                deadline_text=(
                    "Karolinska Institutet's official application guide publishes "
                    "this exact shared application period for master's programmes."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)

    def _programmes(self, html: str) -> list[DiscoveredProgramme]:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for card in soup.select(".ladok-filter-search__result"):
            link = card.select_one("h2 a[href]")
            card_text = normalise(card.get_text(" ", strip=True))
            if link is None or not re.search(r"\bMaster\b", card_text):
                continue
            if not re.search(r"\bProgramme\b", card_text):
                continue
            name = normalise(link.get_text(" ", strip=True))
            if not name or name.casefold().startswith("bachelor"):
                continue
            programme_id = f"karolinska-{slug(name)}"
            source_url = urljoin(CATALOG_URL, link["href"])
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Karolinska Institutet",
                department="Karolinska Institutet",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in Karolinska Institutet's official catalogue. "
                    "The shared application period is represented once at "
                    "institution scope."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Karolinska catalogue contained {len(result)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return result

    @staticmethod
    def _window(html: str) -> tuple[str, str, str]:
        text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        match = _WINDOW_RE.search(text)
        if match is None:
            raise ValueError(
                "Karolinska's exact master's application period is missing"
            )
        opens_at = datetime.strptime(match.group("opens"), "%d %B %Y").date()
        closes_at = datetime.strptime(match.group("closes"), "%d %B %Y").date()
        return (
            opens_at.isoformat(),
            closes_at.isoformat(),
            f"Autumn {match.group('intake_year')}",
        )
