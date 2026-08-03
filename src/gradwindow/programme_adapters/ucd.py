from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://hub.ucd.ie/usis/!W_HU_MENU.P_PUBLISH?p_tag=COURSES&LEVEL=GT"
APPLICATION_URL = "https://www.ucd.ie/graduateadmissions/"
QUERY_URL_RE = re.compile(
    r'"url"\s*:\s*"(?P<url>[^\"]*W_HU_REPORTING\.P_JSON_QUERY[^\"]+)"'
)
MASTER_AWARDS = {
    "LLM",
    "MA",
    "MAcc",
    "MAgrSc",
    "MArch",
    "MBA",
    "MCL",
    "ME",
    "MEd",
    "MEconSc",
    "MEngSc",
    "MFA",
    "MLIS",
    "MMus",
    "MPH",
    "MPP",
    "MPsychSc",
    "MRUP",
    "MSc",
    "MSc(Agr)",
    "MSocSc",
    "ProfMasters",
}


class UCDAdapter(OfficialCatalogAdapter):
    university_id = "university-college-dublin"
    school_prefix = "ucd"
    institution_name = "University College Dublin"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 240
    retrieval_method = "official-course-catalogue-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        match = QUERY_URL_RE.search(wrapper)
        if match is None:
            raise ValueError("UCD course catalogue query was not found")
        fetcher(APPLICATION_URL)
        payload = fetcher(urljoin(CATALOG_URL, match.group("url")))
        return self.parse_catalog(payload)

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        entries = []
        for row in json.loads(payload)["data"]:
            if len(row) < 9 or row[8] != "GT" or row[3] not in MASTER_AWARDS:
                continue
            soup = BeautifulSoup(row[0], "html.parser")
            link = soup.select_one("a.crslink[href]")
            if link is None:
                continue
            entries.append(
                entry(
                    name=link.get_text(" ", strip=True),
                    degree_type=str(row[3]),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
