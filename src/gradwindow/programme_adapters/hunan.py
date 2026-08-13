from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from io import BytesIO

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

GUIDE_URL = "https://gra.hnu.edu.cn/info/1075/10250.htm"
CATALOG_URL = (
    "http://gra.hnu.edu.cn/system/_content/download.jsp?"
    "urltype=news.DownloadAttachUrl&owner=1327586600&wbfileid=16077077"
)
APPLICATION_URL = "https://yz.chsi.com.cn/"
EXPECTED_CATALOG_SHA256 = (
    "8e24e1f23c71740390695a2efbec227e0c734e7eab6b0c49998aeacf1802af63"
)

CatalogueEntries = tuple[tuple[str, str, str, str], ...]
CatalogueFetcher = Callable[[str], CatalogueEntries]


class HunanAdapter:
    university_id = "hunan-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (GUIDE_URL,)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "hunan-national-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 95,
        maximum_expected_programmes: int = 105,
        catalogue_fetcher: CatalogueFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.catalogue_fetcher = catalogue_fetcher or _fetch_catalogue

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(self.catalogue_fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Hunan catalogue contained {len(programmes)} master's routes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        _validate_guide(fetcher(GUIDE_URL))
        programmes.append(_admission_group())
        return DiscoveredCatalog(
            application_opens_at="2025-10-10",
            programmes=programmes,
        )


def _programmes(entries: CatalogueEntries) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_faculty, code, raw_name, raw_mode in entries:
        faculty = normalise(raw_faculty)
        name = normalise(raw_name)
        mode = normalise(raw_mode)
        if not faculty or not code or not name or not mode:
            continue
        mode_id = "part-time" if mode == "非全日制" else "full-time"
        faculty_id = (
            slug(faculty) or hashlib.sha256(faculty.encode("utf-8")).hexdigest()[:10]
        )
        programme_id = f"hunan-{faculty_id}-{code}-{mode_id}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=f"{name}（{mode}）",
            degree_type="Master",
            faculty=faculty,
            department=faculty,
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme and study mode are listed in Hunan University's "
                "official 2026 national master's catalogue. The common exact "
                "registration rounds are represented at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-national-master-catalogue-pdf",
            evidence_quality="official-full-text",
            evidence_document_hash=EXPECTED_CATALOG_SHA256,
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


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
        id="hunan-national-master-admissions",
        name="National master's admissions",
        degree_type="Master",
        faculty="Graduate School",
        department="Graduate Admissions Office",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=(
            "Hunan University's official 2026 guide publishes exact national "
            "master's pre-registration and formal registration periods."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-national-master-guide-html",
        evidence_quality="official-full-text",
    )


def _validate_guide(html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    compact = re.sub(r"\s+", "", text)
    expected = (
        "预报名时间：2025年10月10日至10月13日",
        "正式报名时间：2025年10月16日至10月27日",
    )
    if not all(value in compact for value in expected):
        raise ValueError("Hunan's official 2026 guide lacked its exact rounds")


def _fetch_catalogue(url: str) -> CatalogueEntries:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
    }
    with httpx.Client(follow_redirects=True, timeout=90, headers=headers) as client:
        guide_response = client.get(GUIDE_URL)
        guide_response.raise_for_status()
        response = client.get(url, headers={"Referer": GUIDE_URL})
        response.raise_for_status()
        content = response.content
    if len(content) > 1_000_000 or not content.startswith(b"%PDF"):
        raise ValueError("Hunan source did not return its bounded catalogue PDF")
    if hashlib.sha256(content).hexdigest() != EXPECTED_CATALOG_SHA256:
        raise ValueError("Hunan's 2026 catalogue changed; parser review is required")
    entries: list[tuple[str, str, str, str]] = []
    faculty = "Hunan University"
    with pdfplumber.open(BytesIO(content)) as pdf:
        if len(pdf.pages) != 12:
            raise ValueError("Hunan's 2026 catalogue page count changed")
        for pdf_page in pdf.pages:
            words = pdf_page.extract_words(x_tolerance=2, y_tolerance=2)
            code_words = [
                word
                for word in words
                if 35 < float(word["x0"]) < 100
                and re.fullmatch(r"\d{6}", str(word["text"]))
            ]
            mode_words = [
                word for word in words if str(word["text"]) in {"全日制", "非全日制"}
            ]
            definitions: list[tuple[str, str, str]] = []
            for table in pdf_page.extract_tables():
                for row in table[1:]:
                    if not row or not row[0]:
                        continue
                    lines = [
                        normalise(line)
                        for line in str(row[0]).splitlines()
                        if normalise(line)
                    ]
                    first_code = next(
                        (
                            index
                            for index, line in enumerate(lines)
                            if re.match(r"^\d{6}\s+", line)
                        ),
                        None,
                    )
                    if first_code is None:
                        continue
                    if first_code:
                        faculty = normalise(" ".join(lines[:first_code]))
                    for index, line in enumerate(lines):
                        match = re.match(r"^(\d{6})\s+(.+)$", line)
                        if match is None:
                            continue
                        code, name = match.groups()
                        continuation = index + 1
                        while continuation < len(lines) and not re.match(
                            r"^(?:\d{6}|\d{2})\s+", lines[continuation]
                        ):
                            name += lines[continuation]
                            continuation += 1
                        definitions.append((faculty, code, name))
            if len(definitions) != len(code_words):
                raise ValueError("Hunan catalogue code layout changed")
            for index, definition in enumerate(definitions):
                top = float(code_words[index]["top"])
                next_top = (
                    float(code_words[index + 1]["top"])
                    if index + 1 < len(code_words)
                    else float("inf")
                )
                modes = [
                    str(word["text"])
                    for word in mode_words
                    if top - 2 <= float(word["top"]) < next_top - 2
                ]
                if not modes:
                    raise ValueError("Hunan catalogue study-mode layout changed")
                entries.extend((*definition, mode) for mode in modes)
    return tuple(entries)
