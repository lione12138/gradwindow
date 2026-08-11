from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://iso.hust.edu.cn/info/1194/4653.htm"
APPLICATION_URL = "https://admission.hust.edu.cn/"

_SCHOOLS = (
    "School of Chemistry and Chemical Engineering",
    "School of Mechanical Science and Engineering",
    "School of Materials Science and Engineering",
    "China-EU Institute for Clean and Renewable Energy",
    "School of Electrical and Electronic Engineering",
    "School of Naval Architecture and Ocean Engineering",
    "College of Life Science and Technology",
    "School of Electronic Information and Communication",
    "School of Software Engineering",
    "School of Artificial Intelligence and Automation",
    "School of Integrated Circuits",
    "School of Computer Science and Technology",
    "School of Architecture and Urban Planning",
    "School of Design",
    "School of Civil and Hydraulic Engineering",
    "School of Environmental Science and Engineering",
    "School of Management",
    "School of Economics",
    "College of Public Administration",
    "School of Humanities",
    "School of Law",
    "School of Foreign Languages",
    "School of Journalism and Information Communication",
)
_MEDICAL_UNITS = (
    "Tongji Hospital",
    "Union Hospital",
    "School of Stomatology",
    "School of Nursing",
    "School of Pharmacy",
    "School of Medicine and Health Management",
)
_WINDOW_RE = re.compile(
    r"(?P<open_month>[A-Z][a-z]+)\s+(?P<open_day>\d{1,2})"
    r"(?:st|nd|rd|th)?,\s*"
    r"(?P<open_year>20\d{2})\s+(?:to|through|[-\u2013\u2014])\s+"
    r"(?P<close_month>[A-Z][a-z]+)\s+(?P<close_day>\d{1,2})"
    r"(?:st|nd|rd|th)?,\s*"
    r"(?P<close_year>20\d{2})",
    re.IGNORECASE,
)

PdfTextFetcher = Callable[[str], str]


class HUSTAdapter:
    university_id = "huazhong-university-of-science-and-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-international-admissions-guide-pdf"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "hust-international-graduate-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 100,
        pdf_text_fetcher: PdfTextFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.pdf_text_fetcher = pdf_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        guide_html = fetcher(CATALOG_URL)
        master_url, medical_url = _programme_pdf_urls(guide_html)
        programmes = _main_programmes(self.pdf_text_fetcher(master_url), master_url)
        programmes.extend(
            _medical_programmes(self.pdf_text_fetcher(medical_url), medical_url)
        )
        programmes = sorted(
            {programme.id: programme for programme in programmes}.values(),
            key=lambda item: (item.faculty.casefold(), item.name.casefold()),
        )
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"HUST guides contained {len(programmes)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )

        opens_at, closes_at = _application_window(guide_html)
        programmes.append(
            DiscoveredProgramme(
                id="hust-international-graduate-admissions",
                name="International graduate admissions",
                degree_type="Master/Doctoral",
                faculty="School of International Education",
                department="School of International Education",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International graduate admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=CATALOG_URL,
                        opens_at_basis="official",
                    )
                ],
                deadline_text=(
                    "HUST's official 2026 international graduate guide publishes "
                    "this exact programme-group application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programme_pdf_urls(html: str) -> tuple[str, str]:
    master_url = ""
    medical_url = ""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        url = urljoin(CATALOG_URL, str(link.get("href", "")).strip())
        folded = url.casefold()
        if "202610medicalprograms.pdf" in folded:
            medical_url = url
        elif "2026-masterprograms.pdf" in folded:
            master_url = url
    if not master_url or not medical_url:
        raise ValueError("HUST guide did not link both official 2026 programme PDFs")
    return master_url, medical_url


def _main_programmes(text: str, source_url: str) -> list[DiscoveredProgramme]:
    programmes: list[DiscoveredProgramme] = []
    faculty = "Huazhong University of Science and Technology"
    pending = ""
    in_table = False
    for value in text.splitlines():
        line = normalise(value)
        if not line:
            continue
        if line.startswith("Schools Programs"):
            in_table = True
            pending = ""
            continue
        if line.startswith("Disciplines:"):
            pending = ""
            continue
        if not in_table:
            continue

        matched_school = next(
            (school for school in _SCHOOLS if line.startswith(school)), None
        )
        if matched_school:
            faculty = matched_school
            line = normalise(line[len(matched_school) :])
            pending = ""
            if not line:
                continue

        has_degree_marker = "○" in line or "◎" in line
        name = normalise(re.sub(r"[○◎▷]+", " ", line))
        if not has_degree_marker:
            if name and not name.startswith(("Schools ", "Languages ", "A - ")):
                pending = name
            continue
        if pending:
            name = normalise(f"{pending} {name}")
            pending = ""
        if not name:
            continue
        programmes.append(_programme(name, faculty, source_url))
    return programmes


def _medical_programmes(text: str, source_url: str) -> list[DiscoveredProgramme]:
    programmes: list[DiscoveredProgramme] = []
    faculty = "Tongji Medical College"
    for value in text.splitlines():
        line = normalise(value)
        if not line:
            continue
        matched_unit = next((unit for unit in _MEDICAL_UNITS if unit in line), None)
        if matched_unit and "○" not in line and "◎" not in line:
            faculty = matched_unit
            continue
        if "○" not in line and "◎" not in line:
            continue
        match = re.search(r"([A-Za-z][A-Za-z0-9&'(), /\-]*?)\s+[○◎]", line)
        if match is None:
            continue
        name = normalise(match.group(1))
        if name.startswith(("Master of", "Doctor of")):
            continue
        programmes.append(_programme(name, faculty, source_url))
    return programmes


def _programme(name: str, faculty: str, source_url: str) -> DiscoveredProgramme:
    programme_id = f"hust-{slug(faculty)}-{slug(name)}-master"
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type="Master",
        faculty=faculty,
        department=faculty,
        source_url=source_url,
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text=(
            "Programme is listed in HUST's official 2026 guide. Its shared exact "
            "application period is represented once at programme-group scope."
        ),
        parse_status="no-deadline",
        retrieval_method="official-international-admissions-guide-pdf",
        evidence_quality="official-full-text",
    )


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("HUST guide did not expose its exact application period")
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
        raise ValueError("HUST programme guide did not return a bounded PDF")
    reader = PdfReader(BytesIO(page.raw_bytes))
    return "\f".join(pdf_page.extract_text() or "" for pdf_page in reader.pages)
