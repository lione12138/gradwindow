from __future__ import annotations

from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    entry,
    normalise,
    slug,
)

CATALOG_URL = "https://corsidilaurea.uniroma1.it/en"
APPLICATION_URL = "https://www.uniroma1.it/en/pagina/international-admissions-0"


class SapienzaAdapter(OfficialCatalogAdapter):
    university_id = "sapienza-university-of-rome"
    school_prefix = "sapienza"
    institution_name = "Sapienza University of Rome"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 120
    retrieval_method = "official-degree-course-catalogue"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for card in soup.select("li.corso-card"):
            heading = card.select_one(".corso--header a[href]")
            course_type = card.select_one(".corso--infos .corso--tipologia")
            if heading is None or course_type is None:
                continue
            degree_class = course_type.get_text(" ", strip=True)
            if not degree_class.startswith("LM-") or "c.u." in degree_class.lower():
                continue
            entries.append(
                entry(
                    name=heading.get_text(" ", strip=True),
                    degree_type=f"Laurea Magistrale ({degree_class})",
                    source_url=str(heading["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries

    def _catalog(self, entries: list[CatalogEntry]) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for catalog_entry in entries:
            name = normalise(catalog_entry.name)
            degree_type = normalise(catalog_entry.degree_type)
            source_url = catalog_entry.source_url.strip()
            programme_code = urlsplit(source_url).path.rstrip("/").split("/")[-1]
            if not (name and degree_type and source_url and programme_code):
                continue
            programme_id = f"sapienza-{slug(programme_code)}-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=self.institution_name,
                department=self.institution_name,
                source_url=source_url,
                application_url=self.application_url,
                windows=[],
                deadline_text=(
                    "Programme found in Sapienza's official degree-course "
                    "catalogue. No complete exact opening-and-closing date pair "
                    "was published in the central catalogue, so no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Sapienza catalogue contained {len(result)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
