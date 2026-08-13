from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://formations.umontpellier.fr/fr/formations/master-XB.html"
APPLICATION_URL = (
    "https://www.umontpellier.fr/wp-content/uploads/2025/12/"
    "mm26_affiche_display_1080x1920_03.pdf"
)


class MontpellierAdapter(OfficialCatalogAdapter):
    university_id = "university-of-montpellier"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "montpellier"
    institution_name = "University of Montpellier"
    minimum_expected_programmes = 300
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-expanded-master-catalogue-html"
    catalogue_limitation_reason = (
        "The official catalogue exposes master's mentions and routes. The "
        "national Mon Master calendar covers first-year domestic routes, while "
        "M2 and international procedures vary, so the common calendar is kept "
        "as monitored policy rather than assigned to every programme."
    )

    def __init__(self, minimum_expected_programmes: int = 300) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        for link in soup.select("li.amytis-expanded-list__item a[href]"):
            href = str(link.get("href", ""))
            name = normalise(link.get_text(" ", strip=True))
            if "/fr/formations/master-XB/" not in href or not name:
                continue
            is_route = "amytis-expanded-second-type-list__link" in link.get("class", [])
            if not is_route:
                name = name.title()
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master route" if is_route else "Master",
                    source_url=urljoin(CATALOG_URL, href),
                )
            )
        return rows
