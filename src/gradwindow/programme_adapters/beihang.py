from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from io import BytesIO

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://is.buaa.edu.cn/en/Master-Program-Major-List-of-2026-Beihang.pdf"
GUIDE_URL = "https://is.buaa.edu.cn/en/lxsq/yjs/ssyjs.htm"
APPLICATION_URL = "http://admission.buaa.edu.cn/"

_MARKERS = "\u25cf\u25b2\u25c6\u2610\u25b3"
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_WINDOW_RE = re.compile(
    r"Online Application Start Date:\s*"
    r"(?P<open_month>[A-Z][a-z]+)\s+(?P<open_day>\d{1,2}),\s*"
    r"(?P<open_year>20\d{2}).*?"
    r"Application Deadline:\s*"
    r"(?P<close_month>[A-Z][a-z]+)\s+(?P<close_day>\d{1,2}),\s*"
    r"(?P<close_year>20\d{2})",
    re.IGNORECASE,
)

PdfTextFetcher = Callable[[str], str]


class BeihangAdapter:
    university_id = "beihang-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-international-master-catalogue-pdf"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "beihang-international-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 45,
        maximum_expected_programmes: int = 75,
        pdf_text_fetcher: PdfTextFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.pdf_text_fetcher = pdf_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(self.pdf_text_fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Beihang catalogue contained {len(programmes)} master's "
                f"programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="beihang-international-master-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="International School",
                department="International School",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International master's admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=GUIDE_URL,
                        opens_at_basis="official",
                    )
                ],
                deadline_text=(
                    "Beihang's official 2026 master-program page publishes this "
                    "exact programme-group application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programmes(text: str) -> list[DiscoveredProgramme]:
    lines = [normalise(line) for line in text.splitlines() if normalise(line)]
    names: dict[str, str] = {}
    for index, line in enumerate(lines):
        if not any(marker in line for marker in _MARKERS):
            continue
        if line.casefold().startswith("note:"):
            continue
        candidate = _without_markers(line)
        if _CJK_RE.search(candidate):
            candidate = _next_english_title(lines, index + 1)
        elif not candidate:
            candidate = lines[index - 1] if index else ""
        elif index and _should_join(lines[index - 1], candidate):
            candidate = normalise(f"{lines[index - 1]} {candidate}")
        candidate = normalise(candidate)
        if not _is_programme_title(candidate):
            continue
        names[candidate.casefold()] = candidate

    programmes = []
    for name in sorted(names.values(), key=str.casefold):
        programme_id = f"beihang-{slug(name)}-master"
        programmes.append(
            DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Beihang University",
                department="Beihang University",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme is listed in Beihang's official 2026 international "
                    "master's catalogue. Its shared exact application period is "
                    "represented once at programme-group scope."
                ),
                parse_status="no-deadline",
                retrieval_method="official-international-master-catalogue-pdf",
                evidence_quality="official-full-text",
            )
        )
    return programmes


def _without_markers(value: str) -> str:
    return normalise(
        "".join(" " if character in _MARKERS else character for character in value)
    )


def _next_english_title(lines: list[str], start: int) -> str:
    for line in lines[start : start + 3]:
        candidate = _without_markers(line)
        if not _CJK_RE.search(candidate) and _is_programme_title(candidate):
            return candidate
    return ""


def _should_join(previous: str, candidate: str) -> bool:
    if not _is_title_fragment(previous):
        return False
    endings = (
        " and",
        " of",
        " in",
        " foreign",
        " information",
        " science",
        " technology",
    )
    return previous.casefold().endswith(endings) or not candidate


def _is_title_fragment(value: str) -> bool:
    if _CJK_RE.search(value) or "http" in value.casefold() or len(value) > 90:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z&/-]*", value)
    if not words:
        return False
    connectors = {"and", "of", "in", "for", "to", "the"}
    return all(word.casefold() in connectors or word[0].isupper() for word in words)


def _is_programme_title(value: str) -> bool:
    folded = value.casefold()
    if not value or len(value) > 120 or not re.search(r"[A-Za-z]", value):
        return False
    if _CJK_RE.search(value) or "http" in folded or value.startswith("("):
        return False
    blocked = (
        "school ",
        "major ",
        "note:",
        "taught in ",
        "research field",
        "beihang university",
    )
    return not folded.startswith(blocked)


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("Beihang page did not expose its exact application period")
    return _date(match, "open"), _date(match, "close")


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    return datetime.strptime(value, "%B %d %Y").date().isoformat()


def _fetch_pdf_text(url: str) -> str:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=60,
        max_bytes=1_000_000,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("Beihang catalogue did not return a bounded PDF")
    reader = PdfReader(BytesIO(page.raw_bytes))
    return "\f".join(pdf_page.extract_text() or "" for pdf_page in reader.pages)
