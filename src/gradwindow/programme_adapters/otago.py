from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise

CATALOG_URL = "https://ask.otago.ac.nz/"
PUBLIC_CATALOG_URL = "https://www.otago.ac.nz/study/qualifications"
APPLICATION_URL = "https://www.otago.ac.nz/study/qualifications/apply-for-a-programme"


class OtagoAdapter(BaseProgrammeAdapter):
    university_id = "university-of-otago"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-cloudflare-blocked-catalogue-monitor"
    catalogue_status = "blocked"
    catalogue_limitation_reason = (
        "Otago's public qualifications catalogue is protected by a Cloudflare "
        "challenge; only the official AskOtago availability heartbeat is currently "
        "machine-readable."
    )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        if "AskOtago Service Portal" not in text:
            raise ValueError("Otago official heartbeat did not expose AskOtago")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="otago-masters-programmes",
                    name="Masters programmes",
                    degree_type="Master",
                    faculty="Masters study",
                    department="Masters study",
                    source_url=PUBLIC_CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Otago's public qualifications catalogue, programme pages, "
                        "PDFs, and sitemap currently return a Cloudflare challenge "
                        "to unattended clients. The official AskOtago service is "
                        "monitored as a first-party availability heartbeat. Otago "
                        "publishes only 'most programmes' dates centrally and notes "
                        "programme exceptions, so no exact window is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-access-limitation",
                )
            ],
        )
