from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog
from .official_catalog import normalise

CATALOG_URL = "https://www2.rockefeller.edu/sr-pd/index.php?page=Graduate_Program"


class RockefellerAdapter(BaseProgrammeAdapter):
    university_id = "rockefeller-university"
    catalog_url = CATALOG_URL
    application_url = "https://graduateapplication.rockefeller.edu/"
    intake = "Not applicable"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-doctoral-only-policy"
    catalogue_status = "not-applicable"
    catalogue_limitation_reason = (
        "Rockefeller's official institutional description says it is accredited "
        "to grant the doctoral degree only, so there is no master's admissions "
        "catalogue to publish."
    )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        if "doctoral degree only" not in text.casefold():
            raise ValueError(
                "Rockefeller's official doctoral-only statement is missing"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=[])
