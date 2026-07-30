from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.helsinki.fi/sitemap.xml"
APPLICATION_URL = "https://www.helsinki.fi/en/admissions-and-education/apply-bachelors-and-masters-programmes/apply-international-masters-programmes"
PATH_RE = re.compile(r"^/en/degree-programmes/[^/]+-masters-programme/?$")


class HelsinkiAdapter(OfficialCatalogAdapter):
    university_id = "university-of-helsinki"
    school_prefix = "helsinki"
    institution_name = "University of Helsinki"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 40
    retrieval_method = "official-sitemap"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        sitemap_urls = _locations(fetcher(CATALOG_URL))
        entries = []
        for sitemap_url in sitemap_urls:
            entries.extend(self.extract_entries(fetcher(sitemap_url)))
        return self._catalog(entries)

    def extract_entries(self, xml: str) -> list[CatalogEntry]:
        entries = []
        for source_url in _locations(xml):
            path = urlparse(source_url).path
            if not PATH_RE.fullmatch(path):
                continue
            name = path.rstrip("/").split("/")[-1].removesuffix("-masters-programme")
            entries.append(
                entry(
                    name=f"Master's Programme in {name.replace('-', ' ').title()}",
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _locations(xml: str) -> list[str]:
    return [
        node.text
        for node in ET.fromstring(xml).iter()
        if node.tag.endswith("loc") and node.text
    ]
