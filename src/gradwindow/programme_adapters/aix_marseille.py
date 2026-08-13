from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://formations.univ-amu.fr/rechercher"
APPLICATION_URL = "https://www.univ-amu.fr/fr/candidature-inscription"


class AixMarseilleAdapter(OfficialCatalogAdapter):
    university_id = "aix-marseille-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "aix-marseille"
    institution_name = "Aix-Marseille University"
    minimum_expected_programmes = 105
    window_watch_urls = (
        CATALOG_URL,
        APPLICATION_URL,
        "https://sciences.univ-amu.fr/fr/candidater-master",
    )
    retrieval_method = "official-complete-master-directory-html"
    catalogue_limitation_reason = (
        "Aix-Marseille publishes more than one hundred master mentions in its "
        "official directory. M1 Mon Master, M2 eCandidat, and international "
        "routes use different calendars, so no single date pair is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 105) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("a.diplome_link[href*='/fr/master/']"):
            name = normalise(link.get_text(" ", strip=True))
            href = str(link.get("href", ""))
            if name and href:
                rows.append(
                    CatalogEntry(
                        name=name,
                        degree_type="Master",
                        source_url=urljoin(CATALOG_URL, href),
                    )
                )
        return rows
