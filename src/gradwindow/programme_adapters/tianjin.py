from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://sie.tju.edu.cn/en/xwxm/MASTERPROGRAMS/202510/W020251013367528410002.xlsx"
)
GUIDE_URL = "https://sie.tju.edu.cn/en/xwxm/MASTERPROGRAMS/202510/t20251013_324447.html"
APPLICATION_URL = "https://tju.at0086.cn/student"

_WINDOW_RE = re.compile(
    r"Application\s+Schedule\s*:\s*"
    r"(?P<opens>[A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*"
    r"2\s*0\s*\d\s*\d)"
    r"\s*[-–—]\s*"
    r"(?P<closes>[A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*"
    r"2\s*0\s*\d\s*\d)",
    re.IGNORECASE,
)


class TianjinAdapter:
    university_id = "tianjin-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-2026-international-master-catalogue-xlsx"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "tianjin-international-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 100,
        maximum_expected_programmes: int = 110,
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
                f"Tianjin catalogue contained {len(programmes)} master's "
                f"programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="tianjin-international-master-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="International Education",
                department="International Education",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International master's admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake="Autumn 2026",
                        source_url=GUIDE_URL,
                        opens_at_basis="official",
                    )
                ],
                deadline_text=(
                    "Tianjin University's official 2026 master's guide publishes "
                    "this exact shared application schedule."
                ),
                parse_status="parsed",
                retrieval_method="official-2026-international-master-guide-html",
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(
            application_opens_at=opens_at,
            programmes=programmes,
        )


def _programmes(payload: str) -> list[DiscoveredProgramme]:
    try:
        rows = json.loads(payload)["worksheets"][0]["rows"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            "Tianjin catalogue did not return a readable workbook"
        ) from exc

    entries: list[tuple[str, str, str, str]] = []
    seen_rows: set[tuple[str, str, str, str]] = set()
    for row in rows:
        if not isinstance(row, list) or len(row) < 10:
            continue
        number = str(row[0] or "").strip()
        name = normalise(row[2] or "")
        faculty = normalise(row[4] or "")
        degree_type = normalise(row[7] or "")
        medium = normalise(row[9] or "")
        if not number.isdigit() or not name or "master" not in degree_type.casefold():
            continue
        chinese_name = normalise(row[1] or "")
        identity = (name, faculty, medium, chinese_name)
        if identity in seen_rows:
            continue
        seen_rows.add(identity)
        entries.append(identity)

    duplicate_keys: dict[tuple[str, str, str], set[str]] = {}
    for name, faculty, medium, chinese_name in entries:
        duplicate_keys.setdefault((name, faculty, medium), set()).add(chinese_name)

    programmes: dict[str, DiscoveredProgramme] = {}
    for name, faculty, medium, chinese_name in entries:
        variants = duplicate_keys[(name, faculty, medium)]
        suffix = ""
        display_detail = medium
        if len(variants) > 1:
            suffix = hashlib.sha256(chinese_name.encode("utf-8")).hexdigest()[:8]
            display_detail = f"{medium}; {chinese_name}"
        programme_id = f"tianjin-{slug(faculty)}-{slug(name)}-{slug(medium)}"
        if suffix:
            programme_id = f"{programme_id}-{suffix}"
        display_name = name if not display_detail else f"{name} ({display_detail})"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=display_name,
            degree_type="Master",
            faculty=faculty or "Tianjin University",
            department=faculty or "Tianjin University",
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Tianjin University's official 2026 "
                "international master's workbook. Its shared application "
                "schedule is represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-international-master-catalogue-xlsx",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("Tianjin guide did not expose its exact application schedule")
    return _date(match.group("opens")), _date(match.group("closes"))


def _date(value: str) -> str:
    compact = re.sub(r"(?<=\d)\s+(?=\d)", "", normalise(value))
    compact = re.sub(r"(\d{1,2})(?:st|nd|rd|th)", r"\1", compact, flags=re.I)
    compact = compact.replace(",", "")
    return datetime.strptime(compact, "%B %d %Y").date().isoformat()
