from __future__ import annotations

import json
from urllib.parse import urlparse

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = (
    "https://webapps.grad.uw.edu/SharedElementsPublic/ProgramSearch/GetPrograms"
)
PROGRAM_DIRECTORY_URL = "https://grad.uw.edu/programs/find-a-graduate-program/"
APPLICATION_URL = "https://grad.uw.edu/admission/"


class WashingtonAdapter(OfficialCatalogAdapter):
    university_id = "university-of-washington"
    school_prefix = "washington"
    institution_name = "University of Washington"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    # New official Slate directory: 249 master's rows, including 16 visiting
    # graduate entries (2026-10-05). Retain a floor for the 233 degree entries.
    minimum_expected_programmes = 225
    retrieval_method = "official-programme-api"

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = json.loads(payload)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Washington programme API returned invalid records")
        records = []
        for row in rows:
            if "SlateProgramDegreeLevel" in row:
                level = row["SlateProgramDegreeLevel"]
                name = str(row.get("SlateProgramMarketingName") or "").strip()
                url = str(row.get("ProgramURL") or "").strip()
                code = str(row.get("SlateDegreeCode") or "")
            elif "degree_level" in row:
                level = row["degree_level"]
                name = str(row.get("program_name") or "").strip()
                url = str(row.get("home_page_url") or "").strip()
                code = ""
            else:
                raise ValueError("Washington programme API returned unknown schema")
            if level not in {"Master's", "Masters"}:
                continue
            if code.endswith("VG") or "visiting grad" in name.casefold():
                continue
            if not name or not url:
                raise ValueError(
                    "Washington programme API returned incomplete master's record"
                )
            records.append((name, url))
        return [
            entry(
                name=name,
                degree_type=degree_from(name),
                source_url=self._official_source_url(url),
                base_url=CATALOG_URL,
            )
            for name, url in records
        ]

    @staticmethod
    def _official_source_url(source_url: str) -> str:
        host = (urlparse(source_url).hostname or "").lower()
        if host == "gixnetwork.org" or host.endswith(".gixnetwork.org"):
            return PROGRAM_DIRECTORY_URL
        return source_url
