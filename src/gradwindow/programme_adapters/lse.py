from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.lse.ac.uk/programmes/search-courses"
AVAILABILITY_URL = "https://www.lse.ac.uk/study-at-lse/Graduate/Available-programmes"
APPLICATION_URL = (
    "https://www.lse.ac.uk/study-at-lse/Graduate/Prospective-students/How-to-Apply"
)
PROGRAMME_PATH_RE = re.compile(r"/study-at-lse/graduate/", re.I)
MASTER_RE = re.compile(r"\b(MSc|MA|LLM|MPA|MPH|MRes|Master)\b", re.I)
CODE_RE = re.compile(r"^(?:\*NEW\*\s*)?[A-Z0-9]{4}\s+")


class LSEAdapter(OfficialCatalogAdapter):
    university_id = "london-school-of-economics-and-political-science-lse"
    school_prefix = "lse"
    institution_name = "London School of Economics and Political Science"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (AVAILABILITY_URL, APPLICATION_URL)
    minimum_expected_programmes = 130

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries = []
        expected_start = 1
        expected_total = None
        for page_number in range(1, 51):
            url = (
                CATALOG_URL
                if page_number == 1
                else f"{CATALOG_URL}?pageIndex={page_number}"
            )
            html = fetcher(url)
            text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            match = re.search(r"Showing\s+(\d+)[–-](\d+)\s+results of\s+([\d,]+)", text)
            if match is None:
                raise ValueError("LSE catalogue pagination summary is missing")
            start, end, total = (
                int(value.replace(",", "")) for value in match.groups()
            )
            if (
                start != expected_start
                or not start <= end <= total
                or (expected_total is not None and total != expected_total)
            ):
                raise ValueError("LSE catalogue pagination changed or repeated a page")
            entries.extend(self.extract_entries(html))
            if end == total:
                return self._catalog(entries)
            expected_start, expected_total = end + 1, total
        raise ValueError("LSE catalogue pagination exceeded the 50-page limit")

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PROGRAMME_PATH_RE):
            raw_name = " ".join(link.get_text(" ", strip=True).split())
            if not MASTER_RE.search(raw_name) or re.search(
                r"MPhil|PhD", raw_name, re.I
            ):
                continue
            name = CODE_RE.sub("", raw_name).strip()
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
