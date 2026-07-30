from __future__ import annotations

import re

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.wur.nl/en/education/master/programmes"
APPLICATION_URL = "https://www.wur.nl/en/education/master/application-admission-masters/apply-masters-programme"
RECORD_RE = re.compile(
    r'\\"id\\":\d+,\\"title\\":\\"([^"\\]+)\\".*?\\"path\\":\\"([^"\\]+)',
    re.DOTALL,
)


class WageningenAdapter(OfficialCatalogAdapter):
    university_id = "wageningen-university-and-research"
    school_prefix = "wageningen"
    institution_name = "Wageningen University & Research"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 40
    retrieval_method = "official-embedded-catalogue-data"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        return [
            entry(
                name=name.replace("\\u0026", "&"),
                degree_type="MSc",
                source_url=source_url,
                base_url=CATALOG_URL,
            )
            for name, source_url in RECORD_RE.findall(html)
            if "master" in name.lower()
            and source_url.startswith("/en/education/master/")
            and source_url != "/en/education/master/programmes"
        ]
