from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = (
    "https://www.st-andrews.ac.uk/subjects/course-search/"
    "?mod=false&form=master&num.ranks=500&profile=_default&query=!null"
    "&collection=standrews~sp-web-course--search&sort=metatitle"
    "&f.tabs%7Ctype=Postgraduate"
)
APPLICATION_URL = "https://www.st-andrews.ac.uk/study/apply/postgraduate/"
QUERY_URL_RE = re.compile(r'const queryUrl = "(?P<url>[^"]+)";')
MASTER_RE = re.compile(r"\b(MSc|MRes|MLitt|MPhil|MBA|MPP|Master)\b", re.I)


class StAndrewsAdapter(OfficialCatalogAdapter):
    university_id = "university-of-st-andrews"
    school_prefix = "st-andrews"
    institution_name = "University of St Andrews"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 100
    retrieval_method = "official-course-search-index"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        match = QUERY_URL_RE.search(wrapper)
        if match is None:
            raise ValueError("St Andrews official course query was not found")
        query_url = re.sub(r"num_ranks=\d+", "num_ranks=500", match.group("url"))
        response = httpx.get(
            query_url,
            headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html"},
            timeout=60,
            follow_redirects=True,
        )
        response.raise_for_status()
        return self.parse_catalog(response.text)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for anchor in soup.select("a.search-result__link[href]"):
            name = " ".join(anchor.get_text(" ", strip=True).split())
            if not MASTER_RE.search(name):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=anchor["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
