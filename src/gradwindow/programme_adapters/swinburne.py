from __future__ import annotations

import json
from urllib.parse import urlparse

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.swinburne.edu.au/courses/find-a-course/"
SEARCH_URL = (
    "https://sut-search.funnelback.squiz.cloud/s/search.json?"
    "collection=sut~sp-course-search&query=master&num_ranks=500"
)
APPLICATION_URL = "https://www.swinburne.edu.au/courses/applying/"


class SwinburneAdapter(OfficialCatalogAdapter):
    university_id = "swinburne-university-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "swinburne"
    institution_name = "Swinburne University of Technology"
    minimum_expected_programmes = 45
    window_watch_urls = (CATALOG_URL, SEARCH_URL, APPLICATION_URL)
    retrieval_method = "official-configured-course-search"
    catalogue_limitation_reason = (
        "Swinburne's official course finder configures the public Funnelback "
        "course index used here. Only current master's awards linking back to "
        "official Swinburne course pages are retained. Application dates vary by "
        "course and applicant category."
    )

    def __init__(self, minimum_expected_programmes: int = 45) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        config_html = fetcher(CATALOG_URL)
        if "sut~sp-course-search" not in config_html or "funnelback" not in config_html:
            raise ValueError(
                "Swinburne's official course-search configuration is missing"
            )
        return self.parse_catalog(fetcher(SEARCH_URL))

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        payload = json.loads(html)
        results = payload.get("response", {}).get("resultPacket", {}).get("results", [])
        selected: dict[str, CatalogEntry] = {}
        for result in results:
            name = normalise(result.get("title", ""))
            source_url = str(result.get("liveUrl", ""))
            metadata = result.get("listMetadata", {})
            if not name.startswith(("Master ", "Executive Master ")):
                continue
            if "Current" not in metadata.get("AccreditationStatus", []):
                continue
            hostname = (urlparse(source_url).hostname or "").casefold()
            if hostname not in {"swinburne.edu.au", "www.swinburne.edu.au"}:
                continue
            candidate = CatalogEntry(
                name=name,
                degree_type="Master",
                source_url=source_url,
            )
            previous = selected.get(name)
            if previous is None or _url_score(source_url) < _url_score(
                previous.source_url
            ):
                selected[name] = candidate
        return list(selected.values())


def _url_score(value: str) -> tuple[int, int]:
    parsed = urlparse(value)
    return (len([part for part in parsed.path.split("/") if part]), len(value))
