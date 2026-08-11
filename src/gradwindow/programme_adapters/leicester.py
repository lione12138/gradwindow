from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://le.ac.uk/courses?level=Postgraduate"
APPLICATION_URL = "https://le.ac.uk/study/postgraduates/how-to-apply/applications"
MASTER_CREDENTIAL_RE = re.compile(
    r"\b(LLM|MA|MBA|MEd|MEng|MFA|MPA|MPH|MRes|MSc|Master)\b", re.IGNORECASE
)


class LeicesterAdapter(OfficialCatalogAdapter):
    university_id = "university-of-leicester"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "leicester"
    institution_name = "University of Leicester"
    minimum_expected_programmes = 90
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-postgraduate-course-search"
    catalogue_limitation_reason = (
        "Leicester's official course search exposes the complete taught master's "
        "catalogue. Application timing is course- and intake-specific, and the "
        "central application guide does not publish a common exact window."
    )

    def __init__(self, minimum_expected_programmes: int = 90) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries: list[CatalogEntry] = []
        next_url: str | None = CATALOG_URL
        seen: set[str] = set()
        while next_url and next_url not in seen:
            seen.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            next_url = _next_page_url(html, next_url)
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "apply online" not in guidance or "choose a course" not in guidance:
            raise ValueError(
                "Leicester's official postgraduate application guide is missing"
            )
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for heading in soup.select("h4.search-result-list__title"):
            link = heading.select_one("a[href]")
            if link is None:
                continue
            label = normalise(link.get_text(" ", strip=True))
            match = MASTER_CREDENTIAL_RE.search(label)
            if match is None:
                continue
            name = label if match.start() == 0 else label[: match.start()].rstrip(" ,-")
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type=match.group(1),
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows


def _next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("a.pagination__link--next[href]")
    if link is None or "is-disabled" in (link.get("class") or []):
        return None
    if str(link.get("aria-disabled", "")).casefold() == "true":
        return None
    return urljoin(current_url, str(link["href"]))
