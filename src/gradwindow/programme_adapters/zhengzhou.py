from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise

CATALOG_URL = "https://gs.zzu.edu.cn/info/1025/13630.htm"
GUIDE_URL = "https://gs.zzu.edu.cn/info/1025/13629.htm"
APPLICATION_URL = "https://yz.chsi.com.cn/"


class ZhengzhouAdapter:
    university_id = "zhengzhou-university"
    catalog_url = CATALOG_URL
    guide_url = GUIDE_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    known_programme_window_scope_type = "institution"
    known_programme_window_scope_id = "zhengzhou-university"
    catalogue_status = "blocked"
    catalogue_limitation_reason = (
        "Zhengzhou University's official 2026 directory index lists one PDF per "
        "faculty, but unattended attachment downloads require a human verification "
        "code. Programme titles are therefore not inferred from filenames or snippets."
    )

    def __init__(self, minimum_expected_catalogues: int = 45) -> None:
        self.minimum_expected_catalogues = minimum_expected_catalogues

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        _validate_directory(fetcher(CATALOG_URL), self.minimum_expected_catalogues)
        _validate_guide(fetcher(GUIDE_URL))
        return DiscoveredCatalog(
            application_opens_at="2025-10-10",
            programmes=[_catalogue_monitor(), _deadline_group()],
        )


def _validate_directory(html: str, minimum_expected: int) -> None:
    soup = BeautifulSoup(html, "html.parser")
    text = _compact(soup.get_text(" ", strip=True))
    attachments = {
        str(link.get("href", ""))
        for link in soup.select("a[href*='/system/_content/download.jsp']")
        if "pdf" in normalise(link.get_text(" ", strip=True)).casefold()
    }
    if not all(marker in text for marker in ("郑州大学", "2026年", "招生专业目录")):
        raise ValueError("Zhengzhou's official 2026 catalogue title is missing")
    if len(attachments) < minimum_expected:
        raise ValueError(
            f"Zhengzhou directory exposed {len(attachments)} faculty catalogues; "
            f"expected at least {minimum_expected}"
        )


def _validate_guide(html: str) -> None:
    text = _compact(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if not all(
        marker in text
        for marker in (
            "2025年10月10日至10月13日",
            "2025年10月16日至10月27日",
        )
    ):
        raise ValueError("Zhengzhou's official 2026 registration rounds are missing")


def _catalogue_monitor() -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id="zhengzhou-2026-master-catalogue",
        name="2026 master's programme catalogue",
        degree_type="Master",
        faculty="Graduate School",
        department="Graduate Admissions Office",
        source_url=CATALOG_URL,
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text=(
            "The official index publishes faculty-level 2026 catalogue PDFs, "
            "but their downloads require human verification. This monitor does "
            "not invent programme titles or deadlines."
        ),
        parse_status="no-deadline",
        retrieval_method="official-captcha-protected-catalogue-monitor",
        evidence_quality="official-access-limitation",
    )


def _deadline_group() -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id="zhengzhou-national-master-admissions",
        name="National master's admissions",
        degree_type="Master",
        faculty="Graduate School",
        department="Graduate Admissions Office",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=_national_windows(GUIDE_URL),
        deadline_text=(
            "Zhengzhou University's official 2026 guide publishes the exact "
            "national pre-registration and formal registration periods."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-masters-guide-html",
        evidence_quality="official-full-text",
    )


def _national_windows(source_url: str) -> list[DiscoveredWindow]:
    return [
        DiscoveredWindow(
            round="National master's pre-registration",
            applicant_categories=["domestic-students"],
            opens_at="2025-10-10",
            closes_at="2025-10-13",
            intake="Autumn 2026",
            source_url=source_url,
            opens_at_basis="official",
        ),
        DiscoveredWindow(
            round="National master's formal registration",
            applicant_categories=["domestic-students"],
            opens_at="2025-10-16",
            closes_at="2025-10-27",
            intake="Autumn 2026",
            source_url=source_url,
            opens_at_basis="official",
        ),
    ]


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)
