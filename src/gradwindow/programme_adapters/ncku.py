from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import (
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://oia.ncku.edu.tw/p/404-1032-230753.php?Lang=en"
ADMISSIONS_URL = "https://oia.ncku.edu.tw/p/404-1032-229816.php?Lang=en"
_WINDOW_RE = re.compile(
    r"Spring\s+2027\s+Application.*?Application\s+period\s*:\s*"
    r"(?P<start_month>[A-Z][a-z]+)\s+(?P<start_day>\d{1,2}),\s*"
    r"(?P<start_year>20\d{2})\s*(?:\([^)]*\))?\s*to\s*"
    r"(?P<end_month>[A-Z][a-z]+)\s+(?P<end_day>\d{1,2})\s*"
    r"(?:\([^)]*\))?\s*(?P<end_year>20\d{2})",
    re.IGNORECASE | re.DOTALL,
)
_PREFIX_RE = re.compile(r"^(?:\[[^]]+\]\s*)+")


class NCKUAdapter:
    university_id = "national-cheng-kung-university-ncku"
    catalog_url = CATALOG_URL
    admissions_url = ADMISSIONS_URL
    application_url = ADMISSIONS_URL
    intake = "Spring 2027"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-international-programme-index-and-schedule"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "ncku-international-degree-admissions"

    def __init__(self, minimum_expected_programmes: int = 35) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"NCKU catalogue contained {len(programmes)} international master's "
                f"routes; expected at least {self.minimum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(ADMISSIONS_URL))
        programmes.append(
            DiscoveredProgramme(
                id="ncku-international-degree-programmes",
                name="International degree programmes",
                degree_type="Master/Doctoral",
                faculty="Office of International Affairs",
                department="Office of International Affairs",
                source_url=ADMISSIONS_URL,
                application_url=ADMISSIONS_URL,
                windows=[
                    DiscoveredWindow(
                        round="International degree admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake="Spring 2027",
                        source_url=ADMISSIONS_URL,
                    )
                ],
                deadline_text=(
                    "NCKU's official Spring 2027 international application page "
                    "publishes this exact programme-group application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    programmes = {}
    for table in soup.select("table"):
        faculty = ""
        in_graduate_section = False
        for row in table.select("tr"):
            cells = row.select("th,td")
            if len(cells) == 1:
                label = normalise(cells[0].get_text(" ", strip=True))
                if label == "Graduate":
                    in_graduate_section = True
                    faculty = ""
                elif label == "Undergraduate":
                    in_graduate_section = False
                    faculty = ""
                elif in_graduate_section:
                    faculty = label
                continue
            if not in_graduate_section or len(cells) < 2:
                continue
            raw_name = normalise(cells[0].get_text(" ", strip=True))
            if not raw_name.startswith("[M"):
                continue
            name = normalise(_PREFIX_RE.sub("", raw_name))
            if not name:
                continue
            programme_id = f"ncku-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty or "National Cheng Kung University",
                department=faculty or "National Cheng Kung University",
                source_url=CATALOG_URL,
                application_url=ADMISSIONS_URL,
                windows=[],
                deadline_text=(
                    "Programme is listed in NCKU's official international degree "
                    "programme index. The shared Spring 2027 application period is "
                    "represented once at programme-group scope."
                ),
                parse_status="no-deadline",
                retrieval_method=(
                    "official-international-programme-index-and-schedule"
                ),
                evidence_quality="official-full-text",
            )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("NCKU did not expose its exact Spring 2027 application period")
    return _date(match, "start"), _date(match, "end")


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    return datetime.strptime(value, "%B %d %Y").date().isoformat()
