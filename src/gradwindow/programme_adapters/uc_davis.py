from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://grad.ucdavis.edu/sitemap.xml"
DIRECTORY_URL = "https://grad.ucdavis.edu/graduate-programs"
APPLICATION_URL = "https://www.ucdavis.edu/admissions/graduate-school"


class UCDavisAdapter(OfficialCatalogAdapter):
    """Monitor UC Davis while its programme directory rejects robots."""

    university_id = "university-of-california-davis"
    school_prefix = "uc-davis"
    institution_name = "University of California, Davis"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-sitemap-directory-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "xml")
        urls = {node.get_text(strip=True).rstrip("/") for node in soup.select("loc")}
        if DIRECTORY_URL not in urls:
            raise ValueError("UC Davis sitemap did not expose its graduate directory")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="uc-davis-graduate-programmes",
                    name="Graduate programs directory",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department="Graduate Studies",
                    source_url=DIRECTORY_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "The official sitemap confirms the UC Davis graduate "
                        "programs directory, but the directory currently returns "
                        "HTTP 403 to unattended clients. No names or dates are "
                        "inferred from search snippets."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
