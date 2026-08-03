from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.lancaster.ac.uk/study/postgraduate/postgraduate-courses/"
APPLICATION_URL = (
    "https://www.lancaster.ac.uk/study/postgraduate/applying-for-postgraduate-study/"
)
MASTER_RE = re.compile(r"\b(MSc|MA|MRes|MBA|LLM|MPH|MEd|MEng|MFA|Master)\b", re.I)


class LancasterAdapter(OfficialCatalogAdapter):
    university_id = "lancaster-university"
    school_prefix = "lancaster"
    institution_name = "Lancaster University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 60
    retrieval_method = "official-embedded-catalogue-data"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        listing = next(
            (
                candidate
                for candidate in soup.find_all("course-listing")
                if candidate.get(":courses-data")
            ),
            None,
        )
        if listing is None:
            return []
        rows = json.loads(listing[":courses-data"])
        current_year = (
            str(listing.get(":current-entry-year", "")).strip('"').replace("\\/", "/")
        )
        entries = []
        for row in rows:
            name = row.get("title", "").replace(" : ", " ").strip()
            if (
                row.get("taught") != "1"
                or row.get("entryYear") != current_year
                or not MASTER_RE.search(name)
            ):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=f"/study/postgraduate/postgraduate-courses/{row['slug']}/",
                    base_url=CATALOG_URL,
                )
            )
        return entries
