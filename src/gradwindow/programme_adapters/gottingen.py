from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = (
    "https://www.uni-goettingen.de/en/degree%2Bprogrammes%2Bfrom%2Ba%2Bto%2Bz/"
    "473404.html"
)
ADMISSIONS_URL = "https://www.uni-goettingen.de/en/46537.html"
DEGREE_RE = re.compile(
    r"\((M\.?Sc\.?|M\.?A\.?|MBA|LL\.?M\.?|M\.?Ed\.?|M\.?Eng\.?|M\.?Th\.?S\.?)\)",
    re.IGNORECASE,
)


class GottingenAdapter(OfficialCatalogAdapter):
    university_id = "university-of-gottingen"
    catalog_url = CATALOG_URL
    application_url = ADMISSIONS_URL
    school_prefix = "gottingen"
    institution_name = "University of Göttingen"
    minimum_expected_programmes = 75
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-degree-programmes-a-to-z"
    catalogue_limitation_reason = (
        "Göttingen states that master's application procedures and deadlines "
        "vary by faculty. The A-Z catalogue is complete; faculty deadline pages "
        "remain the next window-discovery phase."
    )

    def __init__(self, minimum_expected_programmes: int = 75) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue = self.parse_catalog(fetcher(CATALOG_URL))
        policy = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "deadlines vary from faculty to faculty" not in policy:
            raise ValueError("Göttingen's faculty-specific deadline policy is missing")
        return catalogue

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("main a[href], article a[href]"):
            label = normalise(link.get_text(" ", strip=True))
            match = DEGREE_RE.search(label)
            lowered = label.casefold()
            if match is None or any(
                marker in lowered for marker in ("refer to", ": s.", "discontinued")
            ):
                continue
            name = normalise(label[: match.start()]).rstrip(" -:")
            rows.append(
                entry(
                    name=name,
                    degree_type=match.group(1),
                    source_url=str(link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return rows
