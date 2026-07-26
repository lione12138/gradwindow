from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "university-of-leeds"
CATALOG_URL = "https://courses.leeds.ac.uk/course-search/masters-courses"
APPLICATION_URL = "https://www.leeds.ac.uk/masters-applying/doc/apply-masters-courses"
DEGREE_RE = re.compile(r"\b(MSc|MA|MRes|MBA|LLM|MPH|MEd|MEng|MFA|MMus|Master)\b", re.I)


class LeedsAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 195) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_html = fetcher(CATALOG_URL)
        first = BeautifulSoup(first_html, "html.parser")
        page_numbers = [
            int(value)
            for link in first.select('a[href*="page="]')
            for value in parse_qs(urlparse(str(link.get("href", ""))).query).get(
                "page", []
            )
        ]
        last_page = max(page_numbers, default=1)
        pages = [first_html]
        pages.extend(
            fetcher(
                f"{CATALOG_URL}?page={page}&start_rank={1 + (page - 1) * 15}&type=PGT&term=202627"
            )
            for page in range(2, last_page + 1)
        )
        return self._catalog(pages)

    def _catalog(self, pages: list[str]) -> DiscoveredCatalog:
        programmes = {}
        for html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for row in soup.select("article.uol-results-items__item"):
                link = row.select_one("h2 a[href]")
                if link is None:
                    continue
                name = link.get_text(" ", strip=True)
                degree_match = DEGREE_RE.search(name)
                if not degree_match:
                    continue
                query = parse_qs(urlparse(str(link.get("href", ""))).query)
                source_url = query.get("url", [str(link.get("href", ""))])[0]
                source_url = urljoin(CATALOG_URL, source_url)
                programme_id = f"leeds-{_slug(name)}"
                if name == "Advanced Computer Science MSc":
                    programme_id = "leeds-advanced-computer-science-msc"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree_match.group(1),
                    faculty="University of Leeds",
                    department="University of Leeds",
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text="Leeds publishes course-specific availability and application guidance but no exact common application opening date. No date is inferred.",
                    parse_status="no-deadline",
                    retrieval_method="official-course-search",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Leeds catalogue contained {len(result)} master's courses; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
