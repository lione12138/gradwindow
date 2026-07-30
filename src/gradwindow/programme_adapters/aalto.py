from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.aalto.fi/sitemap.xml"
APPLICATION_URL = "https://www.aalto.fi/en/study-at-aalto/apply-to-masters-programmes"


class AaltoAdapter(OfficialCatalogAdapter):
    university_id = "aalto-university"
    school_prefix = "aalto"
    institution_name = "Aalto University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 80
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
            if "/en/study-options/" not in path:
                continue
            name_slug = path.rstrip("/").split("/")[-1]
            if "master" not in name_slug or "bachelor" in name_slug:
                continue
            if "master-of-arts" in name_slug:
                degree = "MA"
            elif "master-of-science" in name_slug:
                degree = "MSc"
            else:
                degree = "Master"
            name = (
                re.sub(
                    r"-(?:master-of-(?:science|arts)(?:-[a-z-]+)?|masters?-programme.*|master.*)$",
                    "",
                    name_slug,
                )
                .replace("-", " ")
                .title()
            )
            entries.append(
                entry(
                    name=name,
                    degree_type=degree,
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
