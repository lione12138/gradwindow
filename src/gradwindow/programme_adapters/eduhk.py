from __future__ import annotations

import re
import ssl
from collections.abc import Callable
from io import BytesIO
from urllib.parse import urljoin

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.eduhk.hk/acadprog/postgrad/"
SCHEDULE_URL = (
    "https://www.eduhk.hk/acadprog/downloads/Application_Schedule_for_TPg_202609.pdf"
)
APPLICATION_URL = "https://www.eduhk.hk/onlineappl/"

SourceFetcher = Callable[[str], str]


class EdUHKAdapter:
    university_id = "education-university-of-hong-kong"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "September 2026"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls: tuple[str, ...] = ()
    known_programme_window_scope_type = "programme-group"
    catalogue_limitation_reason = (
        "EdUHK's official 2026/27 schedule says applications opened in October "
        "2025 without an exact day. Its exact closing dates remain review "
        "guidance rather than publishable exact windows."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 48,
        maximum_expected_programmes: int = 55,
        catalogue_fetcher: SourceFetcher | None = None,
        schedule_fetcher: SourceFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.catalogue_fetcher = catalogue_fetcher or _fetch_html
        self.schedule_fetcher = schedule_fetcher or _fetch_schedule

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        del fetcher
        programmes = _programmes(self.catalogue_fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"EdUHK catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        closings = _closing_dates(self.schedule_fetcher(SCHEDULE_URL))
        programmes.extend(_review_groups(closings))
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#content_box_19")
    if section is None or "Taught Postgraduate Programmes" not in normalise(
        section.get_text(" ", strip=True)
    ):
        raise ValueError("EdUHK taught postgraduate catalogue was not found")
    programmes: dict[str, DiscoveredProgramme] = {}
    for link in section.select("a.faq_in_text[href]"):
        name = re.sub(
            r"\s+#\s*$", "", normalise(link.get_text(" ", strip=True))
        ).strip()
        if not name.startswith(("Master", "Executive Master")):
            continue
        source_url = urljoin(CATALOG_URL, str(link.get("href", ""))).rstrip("#")
        container = link.find_parent("div", class_="faq_loop")
        heading = container.select_one(".faq_top strong") if container else None
        faculty = (
            normalise(heading.get_text(" ", strip=True))
            if heading
            else "The Education University of Hong Kong"
        )
        programme_id = f"eduhk-{slug(name)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty=faculty,
            department=faculty,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in EdUHK's official taught postgraduate "
                "directory. The shared opening is month-only and programme "
                "exceptions exist, so no exact programme window is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-taught-postgraduate-directory",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _review_groups(closings: dict[str, str]) -> list[DiscoveredProgramme]:
    definitions = (
        (
            "eduhk-taught-postgraduate-non-local-admissions",
            "Taught postgraduate non-local admissions",
            "Non-local applicant deadline",
            "international-students",
            closings["non-local"],
        ),
        (
            "eduhk-taught-postgraduate-local-admissions",
            "Taught postgraduate local admissions",
            "Local applicant deadline",
            "domestic-students",
            closings["local"],
        ),
    )
    return [
        DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty="Registry",
            department="Registry",
            source_url=SCHEDULE_URL,
            application_url=APPLICATION_URL,
            windows=[
                DiscoveredWindow(
                    round=round_name,
                    applicant_categories=[category],
                    opens_at=None,
                    closes_at=closes_at,
                    intake="September 2026",
                    source_url=SCHEDULE_URL,
                    opens_at_basis="missing",
                )
            ],
            deadline_text=(
                "EdUHK's official 2026/27 schedule gives this exact closing "
                "date but only says applications opened in October 2025. "
                "Programme exceptions also apply, so this remains review guidance."
            ),
            parse_status="incomplete",
            retrieval_method="official-2026-taught-postgraduate-schedule-pdf",
            evidence_quality="official-full-text",
        )
        for programme_id, name, round_name, category, closes_at in definitions
    ]


def _closing_dates(text: str) -> dict[str, str]:
    compact = normalise(text)
    if "October 2025 Open for applications" not in compact:
        raise ValueError("EdUHK schedule lacked its month-only opening wording")
    if re.search(r"10 May 2026.*Non-local Applicants", compact, re.I) is None:
        raise ValueError("EdUHK schedule lacked its non-local closing date")
    if re.search(r"31 May 2026.*Local Applicants", compact, re.I) is None:
        raise ValueError("EdUHK schedule lacked its local closing date")
    return {"non-local": "2026-05-10", "local": "2026-05-31"}


def _legacy_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.options |= ssl.OP_LEGACY_SERVER_CONNECT
    return context


def _fetch_html(url: str) -> str:
    with httpx.Client(
        verify=_legacy_ssl_context(),
        follow_redirects=True,
        timeout=60,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        if len(response.content) > 1_000_000:
            raise ValueError("EdUHK catalogue exceeded its bounded response size")
        return response.text


def _fetch_schedule(url: str) -> str:
    with httpx.Client(
        verify=_legacy_ssl_context(),
        follow_redirects=True,
        timeout=60,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
    if not content.startswith(b"%PDF") or len(content) > 1_000_000:
        raise ValueError("EdUHK schedule did not return a bounded PDF")
    with pdfplumber.open(BytesIO(content)) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError("EdUHK taught postgraduate schedule page count changed")
        return normalise(pdf.pages[0].extract_text() or "")
