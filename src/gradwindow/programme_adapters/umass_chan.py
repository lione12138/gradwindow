from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise

APPLICATION_HEARTBEAT_URL = "https://connect.umassmed.edu/apply/"
PUBLIC_CATALOG_URL = "https://www.umassmed.edu/gsbs/academics/"
ADMISSIONS_URL = (
    "https://www.umassmed.edu/education/"
    "graduate-school-of-biomedical-sciences/admissions/"
)


class UMassChanAdapter(BaseProgrammeAdapter):
    university_id = "university-of-massachusetts-chan-medical-school"
    catalog_url = APPLICATION_HEARTBEAT_URL
    public_catalog_url = PUBLIC_CATALOG_URL
    application_url = APPLICATION_HEARTBEAT_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_HEARTBEAT_URL,)
    catalogue_status = "blocked"
    retrieval_method = "official-application-system-access-monitor"
    catalogue_limitation_reason = (
        "UMass Chan's official GSBS catalogue and admissions pages return a "
        "Cloudflare access-denied response to unattended clients. Its official "
        "application-management page is monitored as a first-party availability "
        "heartbeat; programme names and dates are not copied from search snippets."
    )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        text = normalise(
            BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        ).casefold()
        if not all(
            marker in text
            for marker in (
                "umass med application management",
                "returning users",
                "first-time users",
                "umass chan medical school",
            )
        ):
            raise ValueError("UMass Chan's official application heartbeat changed")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="umass-chan-masters-programmes",
                    name="Graduate master's programmes",
                    degree_type="Master",
                    faculty="Morningside Graduate School of Biomedical Sciences",
                    department="Graduate Admissions",
                    source_url=PUBLIC_CATALOG_URL,
                    application_url=APPLICATION_HEARTBEAT_URL,
                    windows=[],
                    deadline_text=(
                        "UMass Chan's official graduate catalogue currently blocks "
                        "unattended retrieval. This monitor preserves the official "
                        "catalogue and application links without inferring dates."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-access-limitation",
                )
            ],
        )
