from __future__ import annotations

import json
import re

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = (
    "https://uow-search.searchblox.com/rest/v2/api/search"
    "?query=master&pagesize=500&collection=courses&default=AND&col=25"
)
APPLICATION_URL = "https://www.uow.edu.au/study/apply/"
UOW_BASE_URL = "https://www.uow.edu.au/"
COURSE_URL_RE = re.compile(r"^https://www\.uow\.edu\.au/study/courses/master-")


class UOWAdapter(OfficialCatalogAdapter):
    university_id = "university-of-wollongong"
    school_prefix = "uow"
    institution_name = "University of Wollongong"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 150
    retrieval_method = "official-course-search-api"

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        entries: list[CatalogEntry] = []
        for result in json.loads(payload).get("result", []):
            name = str(result.get("coursetitle") or "").strip()
            source_url = str(result.get("url") or "").strip()
            if not name.lower().startswith("master"):
                continue
            if not COURSE_URL_RE.match(source_url):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=source_url,
                    base_url=UOW_BASE_URL,
                )
            )
        return entries
