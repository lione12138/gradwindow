from __future__ import annotations

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://www.qub.ac.uk/courses/postgraduate-taught/"


class QUBAdapter(OfficialCatalogAdapter):
    """Monitor Queen's Belfast while its catalogue requires AWS WAF JS."""

    university_id = "queen-s-university-belfast"
    school_prefix = "qub"
    institution_name = "Queen's University Belfast"
    catalog_url = CATALOG_URL
    application_url = CATALOG_URL
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-aws-waf-catalogue-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        if "awsWafCookieDomainList" not in html or "qub.ac.uk" not in html:
            raise ValueError("QUB catalogue no longer returned its known AWS WAF page")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="qub-postgraduate-taught-programmes",
                    name="Postgraduate taught courses",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department=self.institution_name,
                    source_url=CATALOG_URL,
                    application_url=CATALOG_URL,
                    windows=[],
                    deadline_text=(
                        "The official 2026-27 postgraduate course search requires "
                        "an AWS WAF JavaScript challenge. The challenge page is "
                        "monitored, and no catalogue entries or dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
