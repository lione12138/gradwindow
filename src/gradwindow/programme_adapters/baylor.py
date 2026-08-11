from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.bcm.edu/education/registrar/official-catalogs"
APPLICATION_URL = (
    "https://www.bcm.edu/education/graduate-school-of-biomedical-sciences/"
    "admissions/application-process"
)
BIOMEDICAL_LABEL = "Graduate School of Biomedical Sciences Degree Requirements"
BIOMEDICAL_NAME = "Biomedical Sciences"


class BaylorAdapter(OfficialCatalogAdapter):
    university_id = "baylor-college-of-medicine"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "baylor-medicine"
    institution_name = "Baylor College of Medicine"
    minimum_expected_programmes = 4
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-registrar-degree-requirements"
    catalogue_limitation_reason = (
        "Baylor College of Medicine's official registrar page identifies its "
        "master's degree requirements. Its admissions pages currently describe "
        "the next opening only by month or publish programme-specific dates, so "
        "no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 4) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        for link in soup.select("a[href]"):
            label = normalise(link.get_text(" ", strip=True))
            if label == BIOMEDICAL_LABEL:
                rows.append(
                    CatalogEntry(
                        name=BIOMEDICAL_NAME,
                        degree_type="MS",
                        source_url=urljoin(CATALOG_URL, str(link["href"])),
                    )
                )
                continue
            prefix = "Master of Science in "
            suffix = next(
                (
                    candidate
                    for candidate in (
                        " Program Degree Requirements",
                        " Degree Requirements",
                    )
                    if label.endswith(candidate)
                ),
                None,
            )
            if not label.startswith(prefix) or suffix is None:
                continue
            rows.append(
                CatalogEntry(
                    name=label.removeprefix(prefix).removesuffix(suffix),
                    degree_type="MS",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
