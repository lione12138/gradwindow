from __future__ import annotations

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://sites.cardiff.ac.uk/"
DIRECTORY_URL = "https://www.cardiff.ac.uk/study/postgraduate/taught/courses"
APPLICATION_URL = "https://www.cardiff.ac.uk/study/postgraduate/taught"


class CardiffAdapter(OfficialCatalogAdapter):
    """Monitor Cardiff while Cloudflare blocks unattended catalogue requests."""

    university_id = "cardiff-university"
    school_prefix = "cardiff"
    institution_name = "Cardiff University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (DIRECTORY_URL, APPLICATION_URL)
    retrieval_method = "official-cloudflare-catalogue-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        if "Cardiff University" not in html:
            raise ValueError("Cardiff official-domain heartbeat changed unexpectedly")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="cardiff-postgraduate-taught-programmes",
                    name="Postgraduate taught programmes",
                    degree_type="Master",
                    faculty="Postgraduate taught catalogue",
                    department="Postgraduate taught catalogue",
                    source_url=DIRECTORY_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Cardiff's official taught-course directory currently "
                        "returns a Cloudflare challenge to unattended clients. "
                        "The official domain is monitored and no cached search "
                        "result or date is promoted."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
