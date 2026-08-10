from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise

CATALOG_URL = (
    "https://english.ucas.ac.cn/index.php/admission/international-students/major"
)
NOTICE_INDEX_URL = (
    "https://english.ucas.ac.cn/index.php/admission/international-students/notice"
)
APPLICATION_URL = "https://is.ucas.ac.cn/"
_NOTICE_RE = re.compile(
    r"Call for (?P<year>20\d{2}) Master['’]s/Doctoral Degree Programs "
    r"for International Students",
    re.IGNORECASE,
)
_WINDOW_RE = re.compile(
    r"Application Deadline\s+"
    r"(?P<open_month>[A-Z][a-z]+)\s+(?P<open_day>\d{1,2})\s*"
    r"(?:st|nd|rd|th)?\s*,?\s*(?P<open_year>20\d{2})\s*[-–—]\s*"
    r"(?P<close_month>[A-Z][a-z]+)\s+(?P<close_day>\d{1,2})\s*"
    r"(?:st|nd|rd|th)?\s*,?\s*(?P<close_year>20\d{2})",
    re.IGNORECASE,
)


class UCASAdapter(BaseProgrammeAdapter):
    university_id = "university-of-chinese-academy-of-sciences"
    catalog_url = CATALOG_URL
    admissions_url = NOTICE_INDEX_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, NOTICE_INDEX_URL)
    retrieval_method = "official-international-major-catalogue-and-annual-call"
    known_programme_window_scope_type = "institution"
    known_programme_window_scope_id = "university-of-chinese-academy-of-sciences"

    def __init__(self, minimum_expected_programmes: int = 220) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = self._programmes(fetcher(CATALOG_URL))
        notice_url = self._latest_notice_url(fetcher(NOTICE_INDEX_URL))
        opens_at, closes_at, intake = self._window(fetcher(notice_url))
        programmes.append(
            DiscoveredProgramme(
                id="ucas-international-masters-admissions",
                name="International master's degree admissions",
                degree_type="Master",
                faculty="University of Chinese Academy of Sciences",
                department="International Students Office",
                source_url=notice_url,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International master's degree application period",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=intake,
                        source_url=notice_url,
                    )
                ],
                deadline_text=(
                    "UCAS's annual official international degree call publishes "
                    "this exact university-level application period."
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
        for link in soup.select('a[href*="subjectcode="]'):
            name = normalise(link.get_text(" ", strip=True))
            query = parse_qs(urlparse(link["href"]).query)
            subject_code = query.get("subjectcode", [""])[0].strip()
            if not name or not subject_code:
                continue
            programme_id = f"ucas-{subject_code.lower()}"
            programmes.setdefault(
                programme_id,
                DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type="Master",
                    faculty="University of Chinese Academy of Sciences",
                    department="UCAS faculties and CAS institutes",
                    source_url=urljoin(CATALOG_URL, link["href"]),
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Major found in UCAS's official international-student "
                        "catalogue. The shared international application period is "
                        "represented once at institution scope."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                ),
            )
        result = sorted(
            programmes.values(), key=lambda row: (row.name.casefold(), row.id)
        )
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UCAS catalogue contained {len(result)} unique international "
                f"master's subject codes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return result

    @staticmethod
    def _latest_notice_url(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        notices: list[tuple[int, str]] = []
        for link in soup.find_all("a", href=True):
            text = normalise(link.get_text(" ", strip=True))
            match = _NOTICE_RE.search(text)
            if match:
                notices.append(
                    (int(match.group("year")), urljoin(NOTICE_INDEX_URL, link["href"]))
                )
        if not notices:
            raise ValueError("UCAS's annual international degree call is missing")
        return max(notices)[1]

    @staticmethod
    def _window(html: str) -> tuple[str, str, str]:
        text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        match = _WINDOW_RE.search(text)
        if match is None:
            raise ValueError("UCAS's exact international application period is missing")
        opens_at = datetime.strptime(
            f"{match.group('open_month')} {match.group('open_day')} "
            f"{match.group('open_year')}",
            "%B %d %Y",
        ).date()
        closes_at = datetime.strptime(
            f"{match.group('close_month')} {match.group('close_day')} "
            f"{match.group('close_year')}",
            "%B %d %Y",
        ).date()
        return opens_at.isoformat(), closes_at.isoformat(), f"Autumn {closes_at.year}"
