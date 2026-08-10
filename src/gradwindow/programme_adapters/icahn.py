from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise

HEARTBEAT_URL = "https://grad.icahngraduate.org/"
PUBLIC_CATALOG_URL = "https://icahn.mssm.edu/education/masters"
APPLICATION_URL = "https://icahn.mssm.edu/education/admissions/graduate-education"


class IcahnAdapter(BaseProgrammeAdapter):
    university_id = "icahn-school-of-medicine-at-mount-sinai"
    catalog_url = HEARTBEAT_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (HEARTBEAT_URL,)
    retrieval_method = "officially-linked-catalogue-access-monitor"
    catalogue_status = "blocked"
    catalogue_limitation_reason = (
        "Icahn's official master's catalogue returns an Akamai access-denied "
        "response to unattended clients. Its officially linked graduate-school "
        "site is monitored as a first-party availability heartbeat; programme "
        "names and dates are not copied from search snippets."
    )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        text = normalise(soup.get_text(" ", strip=True)).casefold()
        links = {link.get("href", "") for link in soup.find_all("a", href=True)}
        if (
            "graduate school of biomedical sciences" not in text
            or PUBLIC_CATALOG_URL not in links
        ):
            raise ValueError("Icahn's official graduate-school heartbeat changed")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="icahn-masters-programmes",
                    name="Master's degree programmes",
                    degree_type="Master",
                    faculty="Graduate School of Biomedical Sciences",
                    department="Graduate School of Biomedical Sciences",
                    source_url=PUBLIC_CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Icahn's official catalogue currently blocks unattended "
                        "retrieval. This monitor preserves the official catalogue "
                        "and admissions links without inferring programme dates."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-access-limitation",
                )
            ],
        )
