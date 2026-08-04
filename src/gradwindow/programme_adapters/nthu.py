from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://dgaa.site.nthu.edu.tw/var/file/209/1209/img/499800825.pdf"
ADMISSIONS_INDEX_URL = "https://apply.nthu.edu.tw/en/"

_DEGREES = (
    "Master of Business Administration in Technology Management",
    "Master of Fine Arts in Science and Technology",
    "Master of Arts in Political Economy",
    "Master of Business Administration",
    "Master of Education",
    "Master of Science",
    "Master of Music",
    "Master of Laws",
    "Master of Arts",
)
_SKIP_LINES = {
    "Name of College Name of Department/Institute Name of Degree",
    "Master's Degrees Conferred by National Tsing Hua University",
    "College of Science",
    "College of Engineering",
    "College of Nuclear Science",
    "College of Humanities and Social",
    "Sciences",
    "College of Electrical Engineering",
    "and Computer Science",
    "College of Technology",
    "Management",
    "College of Education",
    "College of Life Sciences and",
    "Medicine",
    "College of Arts",
    "College of Semiconductor",
    "Taipei School of Economics and",
    "Political Science",
}


class NTHUAdapter(BaseProgrammeAdapter):
    university_id = "national-tsing-hua-university"
    catalog_url = CATALOG_URL
    application_url = ADMISSIONS_INDEX_URL
    intake = "Varies by programme"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (ADMISSIONS_INDEX_URL,)
    minimum_expected_programmes = 60

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue_text = fetcher(CATALOG_URL)
        admissions_index = fetcher(ADMISSIONS_INDEX_URL)
        article_url = _latest_admission_url(admissions_index)
        window = _application_window(fetcher(article_url), article_url)
        return self.parse_catalog(catalogue_text, window)

    def parse_catalog(
        self,
        catalogue_text: str,
        shared_window: DiscoveredWindow,
    ) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for name, degree_type in _degree_entries(catalogue_text):
            programme_id = f"nthu-{slug(name)}-{slug(degree_type)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty="National Tsing Hua University",
                department=name,
                source_url=CATALOG_URL,
                application_url=ADMISSIONS_INDEX_URL,
                windows=[],
                deadline_text=(
                    "NTHU's April 2026 official degree list confirms this master's "
                    "programme. Intake availability can vary by department, so the "
                    "central international admissions period is published separately "
                    "at school scope rather than copied onto this programme."
                ),
                parse_status="no-deadline",
                retrieval_method="official-masters-degree-list-pdf",
                evidence_quality="official-full-text",
            )

        scope_id = "nthu-international-graduate-admissions"
        programmes[scope_id] = DiscoveredProgramme(
            id=scope_id,
            name="International graduate admissions",
            degree_type="Master",
            faculty="National Tsing Hua University",
            department="International degree admissions",
            source_url=shared_window.source_url or ADMISSIONS_INDEX_URL,
            application_url=ADMISSIONS_INDEX_URL,
            windows=[shared_window],
            deadline_text=(
                "NTHU's official international admissions announcement publishes "
                f"the {shared_window.intake} application period from "
                f"{shared_window.opens_at} to {shared_window.closes_at}."
            ),
            parse_status="parsed",
            retrieval_method="official-international-admissions-announcement",
            evidence_quality="official-full-text",
        )

        result = sorted(programmes.values(), key=lambda item: item.id)
        degree_count = len(result) - 1
        if degree_count < self.minimum_expected_programmes:
            raise ValueError(
                "NTHU's official degree list contained "
                f"{degree_count} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(
            application_opens_at=shared_window.opens_at,
            programmes=result,
        )


def _degree_entries(text: str) -> list[tuple[str, str]]:
    entries = []
    pending = ""
    for raw_line in text.splitlines():
        line = normalise(raw_line)
        if (
            not line
            or line in _SKIP_LINES
            or line.isdigit()
            or line.startswith("Updated:")
            or line.startswith("A Master’s Degree within")
            or line.startswith("Affiliated College.")
            or line == "to the program website."
        ):
            continue
        if line == "International Intercollegiate Master Program":
            entries.append((line, "Master"))
            pending = ""
            continue
        if line.startswith("Research College of Semiconductor Research Master Program"):
            line = line.removeprefix("Research ")
        pending = normalise(f"{pending} {line}")
        match = _split_degree(pending)
        if match is None:
            continue
        name, degree_type = match
        entries.append((name, degree_type))
        pending = ""
    return entries


def _split_degree(value: str) -> tuple[str, str] | None:
    best: tuple[int, str] | None = None
    for degree in _DEGREES:
        index = value.rfind(f" {degree}")
        if index > 0 and (best is None or index > best[0]):
            best = (index, degree)
    if best is None:
        return None
    index, degree = best
    tail = value[index + 1 :]
    if tail != degree:
        return None
    return normalise(value[:index]), degree


def _latest_admission_url(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    choices = []
    for link in soup.select('a[href*="/en/article/"]'):
        card = link.find_parent("div", class_="card-body")
        text = normalise(card.get_text(" ", strip=True)) if card is not None else ""
        match = re.search(
            r"(?P<season>Spring|Fall)\s+(?P<year>20\d{2})\s+Admission.*?"
            r"(?:International Degree Programs|Graduate Programs)",
            text,
            re.IGNORECASE,
        )
        if match is None or "Application Period:" not in text:
            continue
        season_order = 1 if match.group("season").lower() == "fall" else 0
        choices.append(
            (
                int(match.group("year")),
                season_order,
                urljoin(ADMISSIONS_INDEX_URL, str(link.get("href", ""))),
            )
        )
    if not choices:
        raise ValueError("NTHU's admissions index has no current exact degree window")
    return max(choices)[2]


def _application_window(html: str, source_url: str) -> DiscoveredWindow:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    intake_match = re.search(r"(Spring|Fall)\s+(20\d{2})\s+Admission", text)
    period_match = re.search(
        r"Application Period:\s*"
        r"(?P<opens>[A-Z][a-z]+\s+\d{1,2},\s+20\d{2})\s*[–—-]\s*"
        r"(?P<closes>[A-Z][a-z]+\s+\d{1,2},\s+20\d{2})",
        text,
    )
    if intake_match is None or period_match is None:
        raise ValueError("NTHU's current admissions article lacks an exact period")
    opens_at = datetime.strptime(period_match.group("opens"), "%B %d, %Y").date()
    closes_at = datetime.strptime(period_match.group("closes"), "%B %d, %Y").date()
    return DiscoveredWindow(
        round="International degree application",
        intake=f"{intake_match.group(1).title()} {intake_match.group(2)}",
        applicant_categories=["international-students"],
        opens_at=opens_at.isoformat(),
        closes_at=closes_at.isoformat(),
        source_url=source_url,
    )
