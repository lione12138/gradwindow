from __future__ import annotations

import json
from urllib.parse import urlparse

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://webapps.grad.uw.edu/SharedUIComponents/ProgramSearch/getPrograms"
PROGRAM_DIRECTORY_URL = "https://grad.uw.edu/programs/find-a-graduate-program/"
APPLICATION_URL = "https://grad.uw.edu/admission/"


class WashingtonAdapter(OfficialCatalogAdapter):
    university_id = "university-of-washington"
    school_prefix = "washington"
    institution_name = "University of Washington"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 250
    retrieval_method = "official-programme-api"

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = json.loads(payload)
        return [
            entry(
                name=row["program_name"].strip(),
                degree_type=degree_from(row["program_name"]),
                source_url=self._official_source_url(row["home_page_url"]),
                base_url=CATALOG_URL,
            )
            for row in rows
            if str(row.get("degree_level", "")).strip() == "Masters"
            and str(row.get("program_name", "")).strip()
            and str(row.get("home_page_url", "")).strip()
        ]

    @staticmethod
    def _official_source_url(source_url: str) -> str:
        host = (urlparse(source_url).hostname or "").lower()
        if host == "gixnetwork.org" or host.endswith(".gixnetwork.org"):
            return PROGRAM_DIRECTORY_URL
        return source_url
