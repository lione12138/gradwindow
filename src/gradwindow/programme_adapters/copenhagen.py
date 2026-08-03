from __future__ import annotations

import json

import httpx
from bs4 import BeautifulSoup

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.ku.dk/studies/masters/all-programmes"
FILTER_API_URL = "https://www.ku.dk/studies/study-filter-api/study-filter"
APPLICATION_URL = "https://www.ku.dk/studies/masters/application-and-admission"


class CopenhagenAdapter(OfficialCatalogAdapter):
    university_id = "university-of-copenhagen"
    school_prefix = "copenhagen"
    institution_name = "University of Copenhagen"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (
        APPLICATION_URL,
        "https://www.ku.dk/studies/masters/important-dates-and-deadlines",
    )
    minimum_expected_programmes = 110
    retrieval_method = "official-programme-filter-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        fetcher(CATALOG_URL)
        response = httpx.post(
            FILTER_API_URL,
            json={
                "studyProgrammeType": "20",
                "limit": "200",
                "organizations": "",
                "campaigns": "",
                "layout": "",
                "selectedChildrenSchoolSubjects": "",
                "searchtext": "",
                "topics": "",
                "schoolSubjects": "",
                "bachelorStudySubjects": "",
                "taughtLanguages": "",
                "offset": "0",
            },
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
                "Referer": CATALOG_URL,
            },
            timeout=60,
            follow_redirects=True,
        )
        response.raise_for_status()
        return self.parse_catalog(response.text)

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        html = json.loads(payload)["studyProgrammes"]
        soup = BeautifulSoup(html, "html.parser")
        return [
            entry(
                name=anchor.get_text(" ", strip=True),
                degree_type="Master",
                source_url=anchor["href"],
                base_url=CATALOG_URL,
            )
            for anchor in soup.select("article[data-study-programme] a[href]")
            if anchor.get_text(" ", strip=True)
        ]
