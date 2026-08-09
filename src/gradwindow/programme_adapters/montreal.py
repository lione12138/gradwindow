from __future__ import annotations

from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://admission.umontreal.ca/sitemap.xml"
APPLICATION_URL = "https://admission.umontreal.ca/programmes/"
MASTERS_URL = (
    "https://admission.umontreal.ca/programmes-de-cycles-superieurs/maitrises/"
)


class MontrealAdapter(OfficialCatalogAdapter):
    university_id = "university-of-montreal"
    school_prefix = "umontreal"
    institution_name = "Université de Montréal"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, MASTERS_URL, APPLICATION_URL)
    retrieval_method = "official-programme-sitemaps"

    def __init__(self, minimum_expected_programmes: int = 120) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        sitemap_urls = [
            url
            for url in _locations(fetcher(CATALOG_URL))
            if "sitemap=programmes" in url
        ]
        if not sitemap_urls:
            raise ValueError("UdeM sitemap did not expose programme sitemaps")
        entries = []
        for sitemap_url in sitemap_urls:
            entries.extend(self.extract_entries(fetcher(sitemap_url)))
        catalog = self._catalog(entries)
        for programme in catalog.programmes:
            if programme.name == "Maîtrise en informatique":
                programme.id = "umontreal-maitrise-informatique"
        return catalog

    def extract_entries(self, xml: str) -> list[CatalogEntry]:
        entries = []
        for source_url in _locations(xml):
            path = unquote(urlparse(source_url).path).rstrip("/")
            slug = path.rsplit("/", 1)[-1]
            if not slug.startswith("maitrise-"):
                continue
            name = "Maîtrise " + slug.removeprefix("maitrise-").replace("-", " ")
            entries.append(
                entry(
                    name=normalise(name),
                    degree_type="Maîtrise",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _locations(xml: str) -> list[str]:
    soup = BeautifulSoup(xml, "xml")
    return ["".join(node.get_text().split()) for node in soup.select("loc")]
