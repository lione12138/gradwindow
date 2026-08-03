from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://studiekiezer.ugent.be/sitemap.xml"
APPLICATION_URL = (
    "https://www.ugent.be/prospect/en/administration/application/application-degree"
)
LOWERCASE_WORDS = {"and", "for", "in", "of", "the", "with"}


class GhentAdapter(OfficialCatalogAdapter):
    university_id = "ghent-university"
    school_prefix = "ghent"
    institution_name = "Ghent University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 40
    retrieval_method = "official-english-programme-sitemap"

    def extract_entries(self, xml: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(xml, "xml")
        entries = []
        for node in soup.find_all("loc"):
            source_url = node.get_text(strip=True)
            slug = urlparse(source_url).path.strip("/")
            if not slug.startswith("master-") or not slug.endswith("-en"):
                continue
            name = self._name_from_slug(slug.removesuffix("-en"))
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries

    @staticmethod
    def _name_from_slug(slug: str) -> str:
        words = []
        for index, word in enumerate(slug.split("-")):
            if word.isupper():
                words.append(word)
            elif index and word in LOWERCASE_WORDS:
                words.append(word)
            else:
                words.append(word.capitalize())
        return " ".join(words)
