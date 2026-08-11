from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://www.meduniwien.ac.at/web/en/studies-further-education/study-programmes/"
)
APPLICATION_URL = CATALOG_URL


class MedUniViennaAdapter(OfficialCatalogAdapter):
    university_id = "medical-university-of-vienna"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "meduni-vienna"
    institution_name = "Medical University of Vienna"
    minimum_expected_programmes = 3
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-degree-programmes-page"
    catalogue_limitation_reason = (
        "MedUni Vienna's official degree-programmes page identifies its current "
        "master's programmes. Admissions dates are controlled by the individual "
        "programme pages, so no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 3) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        choices: dict[str, tuple[int, CatalogEntry]] = {}
        for link in soup.select("a[href]"):
            label = normalise(link.get_text(" ", strip=True))
            folded = label.casefold()
            priority = 1
            if folded.startswith("medical informatics master"):
                name = "Medical Informatics"
                priority = 2 if "new" in folded else 1
            elif "molecular precision medicine" in folded and "master" in folded:
                name = "Molecular Precision Medicine"
            elif folded.startswith("masterstudium psychotherapie"):
                name = "Psychotherapy"
            else:
                continue
            candidate = CatalogEntry(
                name=name,
                degree_type="Master",
                source_url=urljoin(CATALOG_URL, str(link["href"])),
            )
            if priority > choices.get(name, (0, candidate))[0]:
                choices[name] = (priority, candidate)
        return [item[1] for item in choices.values()]
