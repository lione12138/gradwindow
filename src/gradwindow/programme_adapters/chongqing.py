from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://yz.cqu.edu.cn/sszyml/2026/index.html"
APPLICATION_URL = "https://yz.chsi.com.cn/"
_FACULTY_PATH_RE = re.compile(r"^/sszyml/2026/\d+\.html$")
_PROGRAMME_RE = re.compile(
    r"^（(?P<mode>全日制|非全日制)）\s*"
    r"(?P<code>\d{6}|\d{4}[A-Z]\d)\s+"
    r"(?P<name>.+?)(?:\s+研究方向：|$)"
)


class ChongqingAdapter:
    university_id = "chongqing-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    catalogue_limitation_reason = (
        "Chongqing University's official 2026 guide delegates national "
        "registration timing to the Ministry of Education and does not publish "
        "an exact university-owned date pair, so no window is inferred."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 100,
        maximum_expected_programmes: int = 115,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        root_html = fetcher(CATALOG_URL)
        root_text = normalise(
            BeautifulSoup(root_html, "html.parser").get_text(" ", strip=True)
        )
        if "所有考生均须在教育部规定时间内参加网上报名和网上确认" not in root_text:
            raise ValueError("Chongqing's official registration policy is missing")
        sources = _faculty_sources(root_html)
        programmes: dict[str, DiscoveredProgramme] = {}
        for faculty, source_url in sources:
            for code, name, mode in _faculty_programmes(fetcher(source_url)):
                faculty_id = (
                    slug(faculty)
                    or hashlib.sha256(faculty.encode("utf-8")).hexdigest()[:10]
                )
                mode_id = "part-time" if mode == "非全日制" else "full-time"
                programme_id = f"chongqing-{faculty_id}-{code}-{mode_id}"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=f"{name}（{mode}）",
                    degree_type="Master",
                    faculty=faculty,
                    department=faculty,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Programme and study mode are listed in Chongqing "
                        "University's official 2026 catalogue. Its guide "
                        "delegates registration timing to the Ministry of "
                        "Education, so no exact dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-2026-faculty-catalogue-html",
                    evidence_quality="official-full-text",
                )
        rows = sorted(
            programmes.values(),
            key=lambda item: (item.faculty.casefold(), item.name.casefold()),
        )
        if not (
            self.minimum_expected_programmes
            <= len(rows)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Chongqing catalogue contained {len(rows)} master's routes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=rows)


def _faculty_sources(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    sources: dict[str, str] = {}
    for link in soup.select("a[href]"):
        path = str(link.get("href", ""))
        faculty = normalise(link.get_text(" ", strip=True))
        if faculty and _FACULTY_PATH_RE.fullmatch(path):
            sources[urljoin(CATALOG_URL, path)] = faculty
    if not sources:
        raise ValueError("Chongqing catalogue did not expose faculty pages")
    return [(faculty, url) for url, faculty in sources.items()]


def _faculty_programmes(html: str) -> list[tuple[str, str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for table_row in soup.select("table tr"):
        first_cell = table_row.find("td")
        if first_cell is None:
            continue
        text = normalise(first_cell.get_text(" ", strip=True))
        match = _PROGRAMME_RE.match(text)
        if match is not None:
            rows.append(
                (
                    match.group("code"),
                    normalise(match.group("name")),
                    match.group("mode"),
                )
            )
    return rows
