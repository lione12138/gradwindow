from __future__ import annotations

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://web.ub.edu/robots.txt"
DIRECTORY_URL = (
    "https://web.ub.edu/ca/web/estudis/cercador-masters-postgraus?"
    "TipologiaDEnsenyament=5741411"
)
APPLICATION_URL = "https://web.ub.edu/ca/web/estudis/masters-postgraus"


class BarcelonaAdapter(OfficialCatalogAdapter):
    """Monitor UB while Cloudflare blocks its searchable master's catalogue."""

    university_id = "university-of-barcelona"
    school_prefix = "barcelona"
    institution_name = "Universitat de Barcelona"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-cloudflare-catalogue-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, text: str) -> DiscoveredCatalog:
        if "Content-Signal:" not in text or "Allow: /" not in text:
            raise ValueError("UB robots policy changed unexpectedly")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="barcelona-university-master-catalogue",
                    name="University master's degree catalogue",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department=self.institution_name,
                    source_url=DIRECTORY_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "The official UB catalogue is protected by Cloudflare and "
                        "returns HTTP 403 to unattended clients. Its official "
                        "robots policy is monitored; no programme names or dates "
                        "are inferred from search results."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
