from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://graduate.as.virginia.edu/graduate-degree-programs"
DEADLINES_URL = "https://graduate.as.virginia.edu/deadlines"
APPLICATION_URL = "https://graduate.as.virginia.edu/apply"
_MASTER_BADGES = {"MA", "MS", "MFA"}
_DEADLINE_SUBJECT_OVERRIDES = {
    ("Chemistry", "MS"): "2026-01-15",
    ("Environmental Sciences", "MS"): "2026-01-15",
    ("Middle Eastern & South Asian Languages & Cultures", "MA"): "2026-05-01",
    ("Physics", "MS"): "2026-01-15",
    ("Statistics", "MS"): "2026-01-15",
}


class VirginiaAdapter:
    university_id = "university-of-virginia"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Fall 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, DEADLINES_URL)
    catalogue_limitation_reason = (
        "The official Graduate School of Arts & Sciences catalogue and deadline "
        "page cover its master's degrees, not every professional school at UVA. "
        "Programmes marked as paused for the 2025-2026 cycle are retained in the "
        "catalogue but receive no application window."
    )
    known_programme_window_scope_type = "programme"
    known_programme_window_scope_id = None

    def __init__(
        self,
        minimum_expected_programmes: int = 15,
        minimum_expected_deadlines: int = 15,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.minimum_expected_deadlines = minimum_expected_deadlines

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        deadlines_html = fetcher(DEADLINES_URL)
        opening, deadlines = _deadlines(
            deadlines_html,
            minimum_expected_deadlines=self.minimum_expected_deadlines,
        )
        programmes = _programmes(fetcher(CATALOG_URL), opening, deadlines)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"Virginia catalogue contained {len(programmes)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=opening, programmes=programmes)


def _programmes(
    html: str,
    opening: str,
    deadlines: dict[tuple[str, str], str | None],
) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    programmes = []
    for row in soup.select(".views-row"):
        link = row.select_one("a[href*='/graduate-degree-programs/']")
        if link is None:
            continue
        subject = normalise(link.get_text(" ", strip=True))
        source_url = urljoin(CATALOG_URL, str(link["href"]))
        badges = [
            normalise(node.get_text(" ", strip=True))
            for node in row.select(".dp-badge")
            if normalise(node.get_text(" ", strip=True)) in _MASTER_BADGES
        ]
        for degree in badges:
            name = f"{subject} {degree}"
            closes_at = deadlines.get((subject.casefold(), degree)) or (
                _DEADLINE_SUBJECT_OVERRIDES.get((subject, degree))
            )
            paused = (subject.casefold(), degree) in deadlines and closes_at is None
            windows = (
                [
                    _window(
                        subject=subject,
                        degree=degree,
                        opening=opening,
                        closes_at=closes_at,
                    )
                ]
                if closes_at
                else []
            )
            programmes.append(
                DiscoveredProgramme(
                    id=f"virginia-{slug(subject)}-{degree.casefold()}",
                    name=name,
                    degree_type=degree,
                    faculty="Graduate School of Arts & Sciences",
                    department=subject,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=windows,
                    deadline_text=(
                        "The official deadline page marks this programme as paused "
                        "for the 2025-2026 application cycle."
                        if paused
                        else "Official Graduate School opening and programme deadline."
                    ),
                    parse_status="no-deadline" if paused else "parsed",
                    retrieval_method="official-gsas-degree-and-deadline-pages",
                    evidence_quality="official-full-text",
                )
            )
    return sorted(programmes, key=lambda item: item.name.casefold())


def _deadlines(
    html: str, *, minimum_expected_deadlines: int
) -> tuple[str, dict[tuple[str, str], str | None]]:
    soup = BeautifulSoup(html, "html.parser")
    text = normalise(soup.get_text(" ", strip=True))
    if "application portal for all degree programs opens on October 1" not in text:
        raise ValueError("Virginia's official October 1 opening policy is missing")
    if "2025-2026 cycle" not in text:
        raise ValueError("Virginia's official cycle label is missing")

    deadlines: dict[tuple[str, str], str | None] = {}
    degree = ""
    for heading in soup.select("h2, h3"):
        heading_text = normalise(heading.get_text(" ", strip=True))
        if heading.name == "h2":
            degree = {
                "Master of Art": "MA",
                "Master of Fine Arts": "MFA",
                "Master of Science": "MS",
            }.get(heading_text, "")
            continue
        if not degree:
            continue
        closes_at = _deadline_date(heading_text)
        if closes_at is None:
            continue
        sibling = heading.find_next_sibling()
        paragraphs = []
        while sibling is not None and sibling.name not in {"h2", "h3"}:
            if sibling.name == "p":
                paragraphs.append(normalise(sibling.get_text(" ", strip=True)))
            sibling = sibling.find_next_sibling()
        subject_text = paragraphs[-1] if paragraphs else ""
        for subject in _subjects(subject_text):
            paused = (
                "applications paused" in subject.casefold()
                or "not accepting" in subject.casefold()
            )
            clean = normalise(re.sub(r"\s*\([^)]*\)", "", subject))
            if clean.startswith("Politics-"):
                clean = "Politics"
            if clean:
                deadlines[(clean.casefold(), degree)] = None if paused else closes_at
    if len(deadlines) < minimum_expected_deadlines:
        raise ValueError("Virginia's master's deadline table is incomplete")
    return "2025-10-01", deadlines


def _subjects(value: str) -> list[str]:
    prefixes = ("The following programs accept applications through May 1,",)
    if value.startswith(prefixes):
        return []
    return [normalise(item) for item in value.split(",") if normalise(item)]


def _deadline_date(value: str) -> str | None:
    folded = value.casefold()
    if "may 1" in folded:
        return "2026-05-01"
    dates = {
        "december 1": "2025-12-01",
        "december 15": "2025-12-15",
        "january 15": "2026-01-15",
        "march 1": "2026-03-01",
    }
    for label, result in dates.items():
        if label in folded:
            return result
    return None


def _window(*, subject: str, degree: str, opening: str, closes_at: str):
    from .base import DiscoveredWindow

    return DiscoveredWindow(
        round=f"{subject} {degree} application",
        opens_at=opening,
        closes_at=closes_at,
        applicant_categories=["all"],
        intake="Fall 2026",
        source_url=DEADLINES_URL,
        opens_at_basis="official",
    )
