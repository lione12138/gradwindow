from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.rmit.edu.au/sitemap.xml"
APPLICATION_URL = "https://www.rmit.edu.au/study-with-us/applying-to-rmit/local-student-applications/how-to-apply/postgraduate-study"
PATH_RE = re.compile(
    r"^/study-with-us/levels-of-study/postgraduate-study/masters-by-coursework/master-of-[^/]+$"
)


class RMITAdapter(OfficialCatalogAdapter):
    university_id = "rmit-university"
    school_prefix = "rmit"
    institution_name = "RMIT University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 60
    retrieval_method = "official-sitemap"

    def extract_entries(self, xml: str) -> list[CatalogEntry]:
        entries = []
        for node in ET.fromstring(xml).iter():
            if not node.tag.endswith("loc") or not node.text:
                continue
            path = urlparse(node.text).path.rstrip("/")
            if not PATH_RE.fullmatch(path):
                continue
            name_slug = re.sub(r"-mc\d+$", "", path.split("/")[-1])
            name = name_slug.replace("-", " ").title()
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=node.text,
                    base_url=CATALOG_URL,
                )
            )
        return entries
