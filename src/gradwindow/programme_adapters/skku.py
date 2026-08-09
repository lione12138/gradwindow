from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

GENERAL_URL = "https://www.skku.edu/eng/edu/graduateSchool/graduate_school.do"
SPECIAL_URL = "https://www.skku.edu/eng/edu/graduateSchool/graduate_school02.do"
PROFESSIONAL_URL = "https://www.skku.edu/eng/edu/graduateSchool/graduate_school03.do"
APPLICATION_URL = "https://admission-global.skku.edu/eng/"


class SKKUAdapter(OfficialCatalogAdapter):
    university_id = "sungkyunkwan-university"
    school_prefix = "skku"
    institution_name = "Sungkyunkwan University"
    catalog_url = GENERAL_URL
    application_url = APPLICATION_URL
    window_watch_urls = (
        GENERAL_URL,
        SPECIAL_URL,
        PROFESSIONAL_URL,
        APPLICATION_URL,
    )
    minimum_expected_programmes = 35
    retrieval_method = "official-graduate-school-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries: list[CatalogEntry] = []
        for source_url in (GENERAL_URL, SPECIAL_URL, PROFESSIONAL_URL):
            entries.extend(self.extract_entries(fetcher(source_url), source_url))
        fetcher(APPLICATION_URL)
        return self._catalog(entries)

    def extract_entries(
        self, html: str, source_url: str = GENERAL_URL
    ) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for heading in soup.select(".wel_txtcont h4"):
            if "popup-subtit" in (heading.get("class") or []):
                continue
            name = heading.get_text(" ", strip=True)
            if not name:
                continue
            if not name.lower().startswith(("graduate school", "skk gsb", "school of")):
                name = f"Graduate Studies in {name}"
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                    base_url=GENERAL_URL,
                )
            )
        return entries
