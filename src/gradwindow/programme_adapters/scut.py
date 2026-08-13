from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise

CATALOG_URL = "https://yanzhao.scut.edu.cn/open/Master/Zsml_view.aspx"
GUIDE_URL = "https://yz.scut.edu.cn/2025/1009/c30111a604485/page.htm"
APPLICATION_URL = "https://yz.chsi.com.cn/"


class SCUTAdapter:
    university_id = "south-china-university-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "scut-national-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 95,
        maximum_expected_programmes: int = 105,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"SCUT catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        _validate_guide(fetcher(GUIDE_URL))
        programmes.append(_admission_group())
        return DiscoveredCatalog(
            application_opens_at="2025-10-10",
            programmes=programmes,
        )


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    programme_select = soup.select_one("#contentParent_drpZy")
    if programme_select is None:
        raise ValueError("SCUT catalogue did not expose its programme selector")
    programmes: dict[str, DiscoveredProgramme] = {}
    for option in programme_select.select("option"):
        label = normalise(option.get_text(" ", strip=True))
        if "|" not in label:
            continue
        code, name = (normalise(part) for part in label.split("|", 1))
        if not re.fullmatch(r"\d{6}|\d{4}[A-Z]\d", code) or not name:
            continue
        programme_id = f"scut-{code}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty="South China University of Technology",
            department="South China University of Technology",
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in SCUT's official 2026 national master's "
                "catalogue. The common exact registration rounds are represented "
                "once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-national-master-catalogue-html",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _admission_group() -> DiscoveredProgramme:
    windows = [
        DiscoveredWindow(
            round="National master's pre-registration",
            applicant_categories=["domestic-students"],
            opens_at="2025-10-10",
            closes_at="2025-10-13",
            intake="Autumn 2026",
            source_url=GUIDE_URL,
            opens_at_basis="official",
        ),
        DiscoveredWindow(
            round="National master's formal registration",
            applicant_categories=["domestic-students"],
            opens_at="2025-10-16",
            closes_at="2025-10-27",
            intake="Autumn 2026",
            source_url=GUIDE_URL,
            opens_at_basis="official",
        ),
    ]
    return DiscoveredProgramme(
        id="scut-national-master-admissions",
        name="National master's admissions",
        degree_type="Master",
        faculty="Graduate School",
        department="Graduate Admissions Office",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=(
            "SCUT's official 2026 guide publishes exact national master's "
            "pre-registration and formal registration periods."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-national-master-guide-html",
        evidence_quality="official-full-text",
    )


def _validate_guide(html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    compact = re.sub(r"\s+", "", text)
    expected = (
        "网上报名时间为2025年10月16日至10月27日",
        "网上预报名时间为2025年10月10日至10月13日",
    )
    if not all(value in compact for value in expected):
        raise ValueError("SCUT's official 2026 guide lacked its exact rounds")
