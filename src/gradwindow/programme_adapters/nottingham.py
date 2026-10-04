from __future__ import annotations

import concurrent.futures
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "the-university-of-nottingham"
CATALOG_URL = "https://www.nottingham.ac.uk/pgstudy/courses/courses.aspx"
APPLICATION_URL = "https://www.nottingham.ac.uk/pgstudy/how-to-apply/apply-online.aspx"
COURSE_RE = re.compile(
    r"^/pgstudy/course/(?:taught|research)/(?P<slug>[^/]+-(?P<award>"
    r"msc|ma|mba|mres|mph|mfa|march|llm|med|mmus|mphil))$",
    re.I,
)
TAUGHT_PATH_RE = re.compile(r"^/pgstudy/course/taught/(?P<slug>[^/]+)$", re.I)
CARD_AWARD_RE = re.compile(
    r"\b(MSc|MA|MBA|MRes|MPH|MFA|MArch|LLM|MEd|MMus|MPhil|MPA|MMedSci)\b",
    re.I,
)


class NottinghamAdapter(BaseProgrammeAdapter):
    """Discover Nottingham master's courses from its A-Z postgraduate search."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(
        self, minimum_expected_programmes: int = 140, *, page_workers: int = 8
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.page_workers = page_workers

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        urls = _letter_urls(first_page)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.page_workers
        ) as executor:
            pages = [first_page, *executor.map(fetcher, urls)]
        fetcher(APPLICATION_URL)
        return self.parse_pages(pages)

    def parse_pages(self, pages: list[str]) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                source_url = (
                    urljoin(CATALOG_URL, str(link["href"])).split("?", 1)[0].rstrip("/")
                )
                parsed_url = urlsplit(source_url)
                if parsed_url.hostname != "www.nottingham.ac.uk":
                    continue
                match = COURSE_RE.fullmatch(parsed_url.path)
                card = link.find_parent(class_="courseDescription")
                heading = card.find("h3") if card is not None else None
                name = _normalise(
                    heading.get_text(" ", strip=True)
                    if heading is not None
                    else link.get_text(" ", strip=True)
                )
                if match is not None:
                    slug = match.group("slug").lower()
                    award = match.group("award").upper()
                else:
                    path_match = TAUGHT_PATH_RE.fullmatch(parsed_url.path)
                    award_match = CARD_AWARD_RE.search(name)
                    if heading is None or path_match is None or award_match is None:
                        continue
                    slug = path_match.group("slug").lower()
                    award = award_match.group(1).upper()
                name = name or _title(slug)
                programme_id = f"nottingham-{slug}"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=award,
                    faculty="University of Nottingham",
                    department="University of Nottingham",
                    source_url=source_url,
                    application_url=source_url,
                    windows=[],
                    deadline_text=(
                        "Nottingham's official postgraduate course search confirms "
                        "this master's course. Deadlines and start dates vary by "
                        "course; no exact opening-and-closing pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-a-z-course-search",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Nottingham's official course search contained "
                f"{len(result)} master's courses; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _letter_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = {
        urljoin(CATALOG_URL, str(link["href"]))
        for link in soup.find_all("a", href=True)
        if re.fullmatch(r"[A-Z]", _normalise(link.get_text(" ", strip=True)))
        and "letter=" in str(link["href"])
    }
    return sorted(urls)


def _title(slug: str) -> str:
    words = [word.capitalize() for word in slug.split("-")]
    acronyms = {
        "Llm": "LLM",
        "Ma": "MA",
        "March": "MArch",
        "Mba": "MBA",
        "Med": "MEd",
        "Mfa": "MFA",
        "Mmus": "MMus",
        "Mphil": "MPhil",
        "Mph": "MPH",
        "Mres": "MRes",
        "Msc": "MSc",
    }
    return " ".join(acronyms.get(word, word) for word in words)


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
