from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.reading.ac.uk/ready-to-study/study/postgraduate-study"
APPLICATION_URL = (
    "https://www.reading.ac.uk/ready-to-study/study/how-to-apply/masters-how-to-apply"
)
SUBJECT_PATH_RE = re.compile(r"/ready-to-study/study/\d{4}/[^/?#]+-pg/?$")
COURSE_PATH_RE = re.compile(r"/ready-to-study/study/\d{4}/[^/?#]+-pg/[^/?#]+/?$")
MASTER_NAME_RE = re.compile(
    r"^(?:MSc|MA|MBA|LLM|MRes|MEd|MEng|MFA|MPH|Master)\b", re.IGNORECASE
)


class ReadingAdapter(OfficialCatalogAdapter):
    university_id = "university-of-reading"
    school_prefix = "reading"
    institution_name = "University of Reading"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 90
    retrieval_method = "official-postgraduate-subject-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index_html = fetcher(CATALOG_URL)
        subject_urls = self.extract_subject_urls(index_html)
        entries: list[CatalogEntry] = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            for html in executor.map(fetcher, subject_urls):
                entries.extend(self.extract_entries(html))
        fetcher(APPLICATION_URL)
        return self._catalog(entries)

    def extract_subject_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = {
            urljoin(CATALOG_URL, str(anchor["href"])).rstrip("/")
            for anchor in soup.select("a[href]")
            if SUBJECT_PATH_RE.search(urlsplit(str(anchor["href"])).path)
        }
        return sorted(urls)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for anchor in soup.select("a[href]"):
            name = anchor.get_text(" ", strip=True)
            source_url = urljoin(CATALOG_URL, str(anchor["href"]))
            if not MASTER_NAME_RE.match(name):
                continue
            if not COURSE_PATH_RE.search(urlsplit(source_url).path):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
