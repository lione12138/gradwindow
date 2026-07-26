from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "city-university-of-hong-kong"
CATALOG_URL = "https://www.cb.cityu.edu.hk/en/pg/taught-postgraduate-programmes/list"
APPLICATION_URL = (
    "https://www.cb.cityu.edu.hk/en/pg/taught-postgraduate-programmes/apply-now"
)


class CityUAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "2026/27"
    application_opens_at_basis = "official"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 65) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = []
        for row in soup.select("tr"):
            dates = row.select_one("[app_start_date]")
            link = row.select_one('a[href*="/programme/"]')
            if dates is None or link is None:
                continue
            name = next(iter(link.stripped_strings), "").strip()
            if not name or name.lower().startswith("postgraduate certificate"):
                continue
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            department = _department(row)
            opens_at = _date(dates.get("app_start_date"))
            windows = []
            for category, attribute in (
                ("domestic-students", "app_deadline"),
                ("international-students", "app_deadline_nl"),
            ):
                closes_at = _date(dates.get(attribute))
                if opens_at and closes_at:
                    windows.append(
                        DiscoveredWindow(
                            round="Main round",
                            opens_at=opens_at,
                            closes_at=closes_at,
                            intake=self.intake,
                            applicant_categories=[category],
                            source_url=CATALOG_URL,
                        )
                    )
            code_node = row.find("td")
            code = " ".join(code_node.stripped_strings) if code_node else ""
            programme_id = f"cityu-{_slug(code)}-{_slug(name)}"
            if name.lower() == "msc computer science":
                programme_id = "cityu-computer-science-msc"
            programmes.append(
                DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=_degree_type(name),
                    faculty=department,
                    department=department,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=windows,
                    deadline_text=(
                        "CityUHK's official 2026/27 programme list publishes the "
                        "exact application opening and closing dates for this programme."
                    ),
                    parse_status="parsed" if windows else "no-deadline",
                    retrieval_method="official-programme-table",
                    evidence_quality="official-full-text",
                )
            )
        programmes.sort(key=lambda item: item.name)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"CityUHK catalogue contained {len(programmes)} master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _department(row) -> str:
    caption = row.find_previous("caption")
    return " ".join(caption.stripped_strings) if caption else "CityUHK"


def _date(value: object) -> str | None:
    try:
        return datetime.strptime(str(value), "%Y/%m/%d %H:%M:%S").date().isoformat()
    except ValueError:
        return None


def _degree_type(name: str) -> str:
    match = re.match(r"(MSc|MA|MSocSc|LLM|MFA|MArch|MBA|EMBA)\b", name, re.I)
    return match.group(1) if match else "Master"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
