from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://www.utm.my/"
APPLICATION_URL = "https://admission.utm.my/international-postgraduate-study/"


class UTMAdapter(OfficialCatalogAdapter):
    """Monitor UTM's central postgraduate directory link.

    The linked Admissions and School of Graduate Studies hosts currently fail
    certificate verification in unattended clients. The official UTM homepage
    remains reachable and provides a deterministic change signal.
    """

    university_id = "universiti-teknologi-malaysia-utm"
    school_prefix = "utm"
    institution_name = "Universiti Teknologi Malaysia"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-postgraduate-directory-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        link = next(
            (
                node
                for node in soup.select("a[href]")
                if "postgraduate programmes"
                in node.get_text(" ", strip=True).casefold()
            ),
            None,
        )
        if link is None:
            raise ValueError("UTM homepage did not expose Postgraduate Programmes")
        source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="utm-postgraduate-programmes",
                    name="Postgraduate programmes directory",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department="School of Graduate Studies",
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "UTM's official homepage links the postgraduate directory. "
                        "The directory hosts currently fail TLS certificate "
                        "verification for unattended clients, so no programme "
                        "names or dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
