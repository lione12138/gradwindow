from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..http_client import FetchFailure
from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme

UNIVERSITY_ID = "ucl-university-college-london"
CATALOG_URL = "https://www.ucl.ac.uk/study/prospective-students/graduate/courses"

_COURSE_PATH_PREFIX = "/prospective-students/graduate/taught-degrees/"
_CATALOG_REFERER = "https://www.ucl.ac.uk/study/prospective-students/graduate"
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/139.0.0.0 Safari/537.36"
)
_DEGREE_RE = re.compile(
    r"\s+(?P<degree>MA \(International\)|MClinDent|MArch|MRes|MASc|MPlan|"
    r"MSc|MPA|MBA|MFA|MPH|MLA|LLM|MA|MS)$"
)
_EXISTING_IDS = {
    "advanced-materials-science-msc": "ucl-advanced-materials-science-msc",
    "computer-graphics-vision-and-imaging-msc": (
        "ucl-computer-graphics-vision-imaging-msc"
    ),
    "computer-science-msc": "ucl-computer-science-msc",
    "data-science-and-machine-learning-msc": ("ucl-data-science-machine-learning-msc"),
    "data-science-msc": "ucl-data-science-msc",
    "machine-learning-msc": "ucl-machine-learning-msc",
    "medical-robotics-and-artificial-intelligence-msc": (
        "ucl-medical-robotics-artificial-intelligence-msc"
    ),
    "robotics-and-artificial-intelligence-msc": (
        "ucl-robotics-artificial-intelligence-msc"
    ),
    "scientific-and-data-intensive-computing-msc": (
        "ucl-scientific-data-intensive-computing-msc"
    ),
    "software-systems-engineering-msc": "ucl-software-systems-engineering-msc",
}

CatalogFallbackFetcher = Callable[[str], str]


def programme_name_key(name: str) -> str:
    """Match typography and degree placement, never fuzzy semantic renames."""
    tokens = re.findall(r"\w+", name.casefold().replace("&", " and "))
    degrees = {
        "msc",
        "ma",
        "mres",
        "march",
        "mclindent",
        "mph",
        "mpa",
        "mfa",
        "masc",
        "mplan",
        "mba",
        "llm",
        "ms",
        "mla",
        "mphil",
    }
    if tokens and tokens[0] in degrees:
        tokens = tokens[1:] + tokens[:1]
    return " ".join(tokens)


class UCLAdapter(BaseProgrammeAdapter):
    """Discover UCL master's courses from its official taught-course finder."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    intake = "Varies by programme"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    browser_fallback_limit = 40
    window_watch_urls = (CATALOG_URL,)

    def __init__(
        self,
        minimum_expected_courses: int = 550,
        minimum_expected_programmes: int = 500,
        blocked_catalog_fetcher: CatalogFallbackFetcher | None = None,
    ) -> None:
        self.minimum_expected_courses = minimum_expected_courses
        self.minimum_expected_programmes = minimum_expected_programmes
        self.blocked_catalog_fetcher = blocked_catalog_fetcher or _fetch_with_curl
        self.previous_ids: dict[str, str] = {}

    def prepare_discovery(self, previous_state: dict) -> None:
        names: dict[str, list[str]] = {}
        for programme_id, item in previous_state.get("programmes", {}).items():
            names.setdefault(
                programme_name_key(_normalise(item.get("name"))), []
            ).append(programme_id)
        self.previous_ids = {
            name: ids[0] for name, ids in names.items() if name and len(ids) == 1
        }

    def parse_catalog_from_fetcher(self, fetcher) -> DiscoveredCatalog:
        try:
            html = fetcher(CATALOG_URL)
        except FetchFailure as exc:
            if exc.kind != "blocked":
                raise
            html = self.blocked_catalog_fetcher(CATALOG_URL)
        if "course-feed-listing-view__result-count" in html:
            from .ucl_current import discover_current_catalogue

            return discover_current_catalogue(
                html,
                fetcher,
                previous_ids=self.previous_ids,
                minimum_courses=self.minimum_expected_courses,
                minimum_programmes=self.minimum_expected_programmes,
            )
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("#programme-data-content .result-item")
        result_count = _result_count(soup)
        if (
            result_count < self.minimum_expected_courses
            or len(cards) < self.minimum_expected_courses
        ):
            raise ValueError(
                "UCL official catalogue only contained "
                f"{min(result_count, len(cards))} taught courses; expected at least "
                f"{self.minimum_expected_courses}"
            )
        programmes = [
            programme
            for card in cards
            if (programme := _programme_from_card(card)) is not None
        ]
        programmes = sorted(programmes, key=lambda item: item.id)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "UCL official catalogue only contained "
                f"{len(programmes)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        if len({programme.id for programme in programmes}) != len(programmes):
            raise ValueError("UCL official catalogue generated duplicate programme IDs")
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _result_count(soup: BeautifulSoup) -> int:
    counter = soup.select_one("#programme-data-content .search-results__result-counter")
    match = re.search(r"Showing\s+(?P<count>\d+)\s+courses", _normalise(counter))
    return int(match.group("count")) if match else 0


def _programme_from_card(card) -> DiscoveredProgramme | None:
    link = card.select_one("a[href]")
    if link is None:
        return None
    name = _normalise(link.get_text(" ", strip=True))
    degree_match = _DEGREE_RE.search(name)
    if degree_match is None:
        return None
    url = str(link.get("href", ""))
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.ucl.ac.uk"
        or not parsed.path.startswith(_COURSE_PATH_PREFIX)
    ):
        raise ValueError(f"UCL catalogue contained a non-official course URL: {url}")
    course_slug = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    affiliation = card.select_one(".search-results__dept")
    faculty, department = _faculty_and_department(_normalise(affiliation))
    return DiscoveredProgramme(
        id=_EXISTING_IDS.get(course_slug, f"ucl-{course_slug}"),
        name=name,
        degree_type=degree_match.group("degree"),
        faculty=faculty,
        department=department,
        source_url=url,
        application_url=url,
        windows=[],
        deadline_text=(
            "UCL's official taught-course finder confirms this master's course. "
            "Application periods are programme-specific and require checking the "
            "course page for the target intake; no date was inferred from the catalogue."
        ),
        parse_status="no-deadline",
        retrieval_method="official-central-taught-course-catalogue-html",
        evidence_quality="official-full-text",
    )


def _faculty_and_department(value: str) -> tuple[str, str]:
    values = [part.strip() for part in value.split("|", 1)]
    faculty = values[0] if values else ""
    department = values[1] if len(values) == 2 else faculty
    if not faculty:
        raise ValueError("UCL course card did not identify its faculty")
    return faculty, department


def _fetch_with_curl(url: str) -> str:
    executable = shutil.which("curl")
    if executable is None:
        raise ValueError("UCL blocked direct access and curl is unavailable")
    result = subprocess.run(
        [
            executable,
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            "45",
            "--referer",
            _CATALOG_REFERER,
            "--header",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "--header",
            "Accept-Language: en-GB,en;q=0.9",
            "--user-agent",
            _BROWSER_USER_AGENT,
            url,
        ],
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"UCL catalogue curl fallback failed: {error}")
    if len(result.stdout) > 2_000_000:
        raise ValueError("UCL catalogue exceeded the download limit")
    html = result.stdout.decode("utf-8", errors="replace")
    if "Just a moment" in html or not any(
        marker in html
        for marker in (
            'id="programme-data-content"',
            "course-feed-listing-view__result-count",
        )
    ):
        raise ValueError("UCL catalogue fallback returned a challenge page")
    return html


def _normalise(value: object) -> str:
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    return " ".join(str(value or "").replace("\xa0", " ").split())
