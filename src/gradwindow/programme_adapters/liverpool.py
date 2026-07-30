from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.liverpool.ac.uk/courses/postgraduate-taught"
APPLICATION_URL = "https://www.liverpool.ac.uk/postgraduate-taught/applying/"
PATH_RE = re.compile(r"^/courses/[^/?#]+/?$")
AWARDS = ("msc-eng", "mres", "msc", "mba", "mph", "med", "meng", "mfa", "ma", "llm")


class LiverpoolAdapter(OfficialCatalogAdapter):
    university_id = "university-of-liverpool"
    school_prefix = "liverpool"
    institution_name = "University of Liverpool"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 160

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            slug = urlparse(link["href"]).path.rstrip("/").split("/")[-1]
            degree = next(
                (award for award in AWARDS if slug.endswith(f"-{award}")), None
            )
            if not degree:
                continue
            name = link.get_text(" ", strip=True)
            entries.append(
                entry(
                    name=f"{name} ({degree.upper()})",
                    degree_type=degree.upper(),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
