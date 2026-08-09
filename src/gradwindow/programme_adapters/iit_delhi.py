from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://home.iitd.ac.in/pg-admissions.php"
APPLICATION_URL = "https://ecampus.iitd.ac.in/PGADM/"


class IITDelhiAdapter(OfficialCatalogAdapter):
    """Monitor IIT Delhi's current PG route without trusting broken TLS pages."""

    university_id = "indian-institute-of-technology-delhi-iitd"
    school_prefix = "iitd"
    institution_name = "Indian Institute of Technology Delhi"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 1
    retrieval_method = "official-current-pg-admissions-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(soup.stripped_strings)
        pg_link = next(
            (
                link
                for link in soup.select("a[href]")
                if "PG Programmes admission" in link.get_text(" ", strip=True)
            ),
            None,
        )
        if "PG ADMISSIONS" not in text or "2026-27" not in text or pg_link is None:
            raise ValueError("IIT Delhi's current PG admissions route changed")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="iit-delhi-postgraduate-programmes",
                    name="Postgraduate programmes",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department="Postgraduate admissions",
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "IIT Delhi's official page links the 2026-27 PG brochure "
                        "and application portal. The academic catalogue and brochure "
                        "hosts currently fail certificate verification for unattended "
                        "clients, so no programme list or date is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
