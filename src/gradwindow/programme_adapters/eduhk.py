from __future__ import annotations

import re
import ssl
from collections.abc import Callable
from io import BytesIO
from urllib.parse import urljoin, urlsplit

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://gs.eduhk.hk/pg-programmes/programme-information.html"
SCHEDULE_URL = "https://www.eduhk.hk/acadprog/postgrad/schedule_index.html"
APPLICATION_URL = "https://www.eduhk.hk/onlineappl/"

SourceFetcher = Callable[[str], str]


class EdUHKAdapter:
    university_id = "education-university-of-hong-kong"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "September 2027"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls: tuple[str, ...] = ()
    known_programme_window_scope_type = "programme-group"
    catalogue_limitation_reason = (
        "EdUHK's general taught postgraduate schedule has programme exceptions "
        "and permits earlier closure when places fill. Programme-specific "
        "applicability needs review; general dates are not copied to each course."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 48,
        maximum_expected_programmes: int = 65,
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
        schedule = self.schedule_fetcher(SCHEDULE_URL)
        if "2027/28" in schedule:
            compact = normalise(schedule)
            for pattern in (
                r"September 2027 Intake",
                r"5 Oct 2026 \(Mon\) Open for Applications",
                r"10 May 2027 \(Mon\) Application Deadline for Non-local Applicants",
                r"31 May 2027 \(Mon\) Application Deadline for Local Applicants",
                r"not applicable to PhD, MPhil, EdD, EdD\(Chinese\), MSocSc\(EP\) and PGDE",
            ):
                if re.search(pattern, compact) is None:
                    raise ValueError("EdUHK 2027 schedule dates or scope changed")
            programmes.extend(
                _review_groups(
                    {"non-local": "2027-05-10", "local": "2027-05-31"},
                    intake_year=2027,
                    opens_at="2026-10-05",
                )
            )
        else:
            closings = _closing_dates(schedule)
            programmes.extend(_review_groups(closings))
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("#content_box_19")
    current = soup.select("#tpp-gs, #tpp-reg")
    if current:
        if len(current) != 2:
            raise ValueError("EdUHK taught catalogue lacked an administering section")
        links = [
            link
            for heading in current
            for link in heading.parent.select(
                "details.programme-section .section-body a[href]"
            )
        ]
    elif section is None or "Taught Postgraduate Programmes" not in normalise(
        section.get_text(" ", strip=True)
    ):
        raise ValueError("EdUHK taught postgraduate catalogue was not found")
    else:
        links = section.select("a.faq_in_text[href]")
    programmes: dict[str, DiscoveredProgramme] = {}
    for link in links:
        parts = []
        for child in link.children:
            if getattr(child, "name", None) == "br":
                break
            parts.append(
                child.get_text(" ", strip=True)
                if hasattr(child, "get_text")
                else str(child)
            )
        label = normalise(" ".join(parts))
        if "*" in label:
            continue  # Official footnote: subject to the University's approval.
        name = re.sub(r"\s+#\s*$", "", label).strip()
        if not name.startswith(("Master", "Executive Master")):
            continue
        source_url = urljoin(CATALOG_URL, str(link.get("href", ""))).rstrip("#")
        host = urlsplit(source_url).hostname or ""
        if host != "eduhk.hk" and not host.endswith(".eduhk.hk"):
            continue
        container = link.find_parent("div", class_="faq_loop")
        heading = container.select_one(".faq_top strong") if container else None
        if current:
            container = link.find_parent("details", class_="programme-section")
            heading = container.select_one("summary strong") if container else None
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
                "directory. General schedule exceptions exist, so no exact "
                "programme-specific window is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-taught-postgraduate-directory",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _review_groups(
    closings: dict[str, str], *, intake_year: int = 2026, opens_at: str | None = None
) -> list[DiscoveredProgramme]:
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
                    opens_at=opens_at,
                    closes_at=closes_at,
                    intake=f"September {intake_year}",
                    source_url=SCHEDULE_URL,
                    opens_at_basis="official" if opens_at else "missing",
                )
            ],
            deadline_text=(
                "Official 2027/28 general taught postgraduate schedule. Programmes "
                "may close earlier when places fill. Not applicable to PhD, MPhil, "
                "EdD, EdD(Chinese), MSocSc(EP) or PGDE. Review programme scope before publication."
            )
            if opens_at
            else (
                "EdUHK's official 2026/27 schedule gives this exact closing "
                "date but only says applications opened in October 2025. "
                "Programme exceptions also apply, so this remains review guidance."
            ),
            parse_status="parsed" if opens_at else "incomplete",
            retrieval_method="official-taught-postgraduate-schedule",
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
    if not url.lower().endswith(".pdf"):
        return normalise(
            BeautifulSoup(_fetch_html(url), "html.parser").get_text(" ", strip=True)
        )
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
