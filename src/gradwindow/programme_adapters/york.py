from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.york.ac.uk/study/postgraduate/courses/all?mode=taught"
APPLICATION_URL = "https://www.york.ac.uk/study/postgraduate-taught/apply/"
PATH_RE = re.compile(
    r"^(?:https?://(?:www\.)?york\.ac\.uk)?/study/postgraduate-taught/courses/[^/?#]+/?$"
)
AWARDS = {"ma", "mba", "med", "meng", "mfa", "llm", "mph", "mres", "msc"}


class YorkAdapter(OfficialCatalogAdapter):
    university_id = "university-of-york"
    school_prefix = "york"
    institution_name = "University of York"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 175

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            slug = urlparse(link["href"]).path.rstrip("/").split("/")[-1]
            award = slug.split("-", 1)[0]
            if award not in AWARDS:
                continue
            entries.append(
                entry(
                    name=f"{link.get_text(' ', strip=True)} ({award.upper()})",
                    degree_type=award.upper(),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
