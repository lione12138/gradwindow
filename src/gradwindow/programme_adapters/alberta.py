from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://calendar.ualberta.ca/index.php?catoid=69"
APPLICATION_URL = "https://www.ualberta.ca/en/graduate-studies/prospective-students/apply-for-admission/index.html"


class AlbertaAdapter(OfficialCatalogAdapter):
    """Monitor UAlberta's current calendar while its directory blocks robots.

    The current Acalog landing page remains machine-readable and identifies the
    2026-27 Graduate Programs section. Its linked catalogue pages and the main
    graduate directory currently return an AWS WAF challenge to unattended
    clients, so this adapter deliberately emits one school-scope monitor record
    instead of fabricating a programme list from search snippets.
    """

    university_id = "university-of-alberta"
    school_prefix = "ualberta"
    institution_name = "University of Alberta"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 1
    retrieval_method = "official-current-calendar-catalogue-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        calendar_name = soup.select_one(".acalog_catalog_name")
        link = next(
            (
                node
                for node in soup.select("a[href]")
                if node.get_text(" ", strip=True) == "Graduate Programs"
            ),
            None,
        )
        if calendar_name is None or "2026-2027" not in calendar_name.get_text(
            " ", strip=True
        ):
            raise ValueError("UAlberta did not expose its current 2026-27 calendar")
        if link is None:
            raise ValueError("UAlberta calendar did not expose Graduate Programs")
        source_url = urljoin(CATALOG_URL, str(link["href"]))
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="ualberta-graduate-programmes",
                    name="Graduate programs catalogue",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department="Faculty of Graduate & Postdoctoral Studies",
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "The official 2026-27 calendar confirms the Graduate "
                        "Programs catalogue, but its detail pages currently require "
                        "AWS browser verification. No programme names or dates are "
                        "inferred from search snippets."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
