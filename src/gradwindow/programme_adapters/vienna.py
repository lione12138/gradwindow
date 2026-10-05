from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = (
    "https://studieren.univie.ac.at/en/find-your-degree-programme/masters-programmes"
)
APPLICATION_URL = (
    "https://studieren.univie.ac.at/en/applying-for-a-programme/admission-info/mag"
)
PATH_RE = re.compile(r"^/en/degree-programmes/master-programmes/[^/?#]+/?$")
CURRENT_PATH_RE = re.compile(
    r"^/en/find-your?-degree-programme/masters-programmes/[^/?#]+-masters-programme/?$"
)


class ViennaAdapter(OfficialCatalogAdapter):
    university_id = "university-of-vienna"
    school_prefix = "vienna"
    institution_name = "University of Vienna"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 105

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=True):
            url = urljoin(CATALOG_URL, str(link["href"]))
            parsed = urlsplit(url)
            name = link.get_text(" ", strip=True)
            if parsed.hostname != "studieren.univie.ac.at" or not name:
                continue
            if not (
                CURRENT_PATH_RE.fullmatch(parsed.path)
                or (PATH_RE.fullmatch(parsed.path) and name.endswith("(Master)"))
            ):
                continue
            entries.append(
                entry(
                    name=name.removesuffix(" (Master)"),
                    degree_type="Master",
                    source_url=url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
