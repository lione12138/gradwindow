from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://coursehandbook.mq.edu.au/sitemap.xml"
APPLICATION_URL = "https://www.mq.edu.au/study/admissions-and-entry/apply"


class MacquarieAdapter(OfficialCatalogAdapter):
    """Monitor Macquarie's official current handbook sitemap.

    The sitemap index is stable and machine-readable, but its large child maps
    currently return an empty body to the project's HTTP client while browsers
    receive the catalogue. Keeping this as an explicit monitor is safer than
    publishing an incomplete list from a single default handbook record.
    """

    university_id = "macquarie-university"
    school_prefix = "macquarie"
    institution_name = "Macquarie University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 1
    retrieval_method = "official-current-handbook-sitemap-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "xml")
        sitemap_urls = [node.get_text(strip=True) for node in soup.select("loc")]
        last_modified = [node.get_text(strip=True) for node in soup.select("lastmod")]
        if not sitemap_urls or not any(
            value.startswith("2026-") for value in last_modified
        ):
            raise ValueError("Macquarie's current handbook sitemap index changed")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="macquarie-2026-course-handbook-catalogue",
                    name="2026 course handbook catalogue",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department="Course handbook",
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Macquarie's official 2026 handbook sitemap is monitored, "
                        "but its child maps currently return empty responses to the "
                        "unattended client. No partial programme list or date is "
                        "published."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
