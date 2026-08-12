from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://admissions.cau.edu.cn/art/2025/9/29/art_48604_1107314.html"
APPLICATION_URL = "http://apply.cau.edu.cn/"


class CAUAdapter(BaseProgrammeAdapter):
    university_id = "china-agricultural-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    catalogue_limitation_reason = (
        "China Agricultural University's 2026 guide publishes application "
        "months, not exact opening and closing dates, so no dates are inferred."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 40,
        maximum_expected_programmes: int = 48,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        programmes = _programmes(html)
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"CAU catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        _verify_month_only_schedule(html)
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    tables = [
        table
        for table in soup.find_all("table")
        if table.find("table") is None
        and "Master" in normalise(table.get_text(" ", strip=True))
        and "Ph.D" in normalise(table.get_text(" ", strip=True))
    ]
    if len(tables) != 2:
        raise ValueError("CAU guide did not expose its two programme tables")
    programmes: dict[str, DiscoveredProgramme] = {}
    for table_index, table in enumerate(tables):
        medium = "English" if table_index == 0 else "Chinese"
        faculty = "China Agricultural University"
        for row in table.find_all("tr"):
            cells = [
                normalise(cell.get_text(" ", strip=True))
                for cell in row.find_all(["th", "td"])
            ]
            if len(cells) < 3:
                continue
            if len(cells) >= 4:
                if cells[0] and "Colleges" not in cells[0]:
                    faculty = _english_label(cells[0])
                raw_name, master_duration = cells[1], cells[2]
            else:
                raw_name, master_duration = cells[0], cells[1]
            if re.search(r"\d\s*years?", master_duration, re.I) is None:
                continue
            name = _english_label(raw_name).replace(" ※", "").strip()
            if not name:
                continue
            programme_id = f"cau-{slug(faculty)}-{slug(name)}-{slug(medium)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=f"{name} ({medium}-medium)",
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme is listed in China Agricultural University's "
                    "official 2026 graduate admission tables. The application "
                    "schedule is month-only, so no exact dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-2026-graduate-guide-html-tables",
                evidence_quality="official-full-text",
            )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _verify_month_only_schedule(html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    compact = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    if re.search(r"Nov 2025 to Feb 2026", compact, re.I) is None:
        raise ValueError("CAU guide lacked its scholarship application months")


def _english_label(value: str) -> str:
    text = normalise(value)
    match = re.search(r"[A-Za-z].*", text)
    return normalise(match.group(0)) if match else ""
