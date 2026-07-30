from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.dtu.dk/english/education/graduate/msc-programmes"
APPLICATION_URL = "https://www.dtu.dk/english/education/graduate/admission-and-deadlines/application_procedure/apply/submit-application"
PATH_RE = re.compile(r"/(?:english/education/graduate/msc-programmes)/[^/?#]+/?$", re.I)


class DTUAdapter(OfficialCatalogAdapter):
    university_id = "technical-university-of-denmark"
    school_prefix = "dtu"
    institution_name = "Technical University of Denmark"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 30

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PATH_RE):
            name = urlparse(link["href"]).path.rstrip("/").split("/")[-1]
            name = name.replace("-", " ").title()
            entries.append(
                entry(
                    name=f"MSc {name}",
                    degree_type="MSc",
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
