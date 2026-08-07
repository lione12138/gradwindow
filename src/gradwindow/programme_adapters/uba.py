from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://exactas.uba.ar/ensenanza/carreras-de-posgrado/maestrias/"


class UBAAdapter(BaseProgrammeAdapter):
    university_id = "universidad-de-buenos-aires"
    catalog_url = CATALOG_URL
    application_url = CATALOG_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 6

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for heading in soup.select("h2.titulo"):
            name = normalise(heading.get_text(" ", strip=True))
            if not name.casefold().startswith("maestr"):
                continue
            link = heading.find_parent("a", href=True)
            source_url = (
                urljoin(CATALOG_URL, str(link.get("href", "")))
                if link is not None
                else CATALOG_URL
            )
            programme_id = f"uba-exactas-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Maestría",
                faculty="Facultad de Ciencias Exactas y Naturales",
                department="Secretaría de Posgrado",
                source_url=source_url,
                application_url=CATALOG_URL,
                windows=[],
                deadline_text=(
                    "The University of Buenos Aires' official Exact and Natural "
                    "Sciences postgraduate directory lists this maestría. This "
                    "adapter currently covers that faculty; UBA's central page "
                    "routes applicants to faculty-managed admissions. No complete "
                    "exact opening-and-closing pair is published on the directory, "
                    "so no dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-uba-exactas-masters-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda programme: programme.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "UBA Exactas' official directory contained "
                f"{len(result)} maestrías; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
