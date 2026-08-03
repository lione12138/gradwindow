from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.tuwien.at/en/studies/studies/master-programmes"
APPLICATION_URL = "https://www.tuwien.at/en/studies/admission"
NAME_RE = re.compile(
    r"^(?:International(?:e)?\s+)?Master[’']?s?\s+Programme\s+",
    re.IGNORECASE,
)


class TUWienAdapter(OfficialCatalogAdapter):
    university_id = "vienna-university-of-technology"
    school_prefix = "tu-wien"
    institution_name = "TU Wien"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 30
    retrieval_method = "official-master-programme-directory"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main") or soup
        entries = []
        for anchor in main.find_all("a", href=True):
            label = " ".join(anchor.get_text(" ", strip=True).split())
            if not NAME_RE.match(label):
                continue
            source_url = urljoin(CATALOG_URL, anchor["href"].strip())
            host = (urlparse(source_url).hostname or "").lower()
            if host != "tuwien.at" and not host.endswith(".tuwien.at"):
                continue
            entries.append(
                entry(
                    name=NAME_RE.sub("", label),
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
