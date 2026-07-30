from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.unibas.ch/en/Studies/Before-My-Studies/Degree-Programs.html?degree=master"
APPLICATION_URL = "https://www.unibas.ch/en/Studies/Before-My-Studies/Application-Admission/Admission/Admission-to-the-master-s-studies.html"


class BaselAdapter(OfficialCatalogAdapter):
    university_id = "university-of-basel"
    school_prefix = "basel"
    institution_name = "University of Basel"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 80

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select("a.newsbox_listing_link[href]"):
            badges = [span.get_text(" ", strip=True) for span in link.find_all("span")]
            if not badges or badges[-1] != "Master":
                continue
            name = badges[0]
            source_url = link["href"].replace("°ree=", "&degree=")
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
