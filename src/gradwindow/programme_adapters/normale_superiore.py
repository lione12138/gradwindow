from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.sns.it/en/didactic-offer"
APPLICATION_URL = "https://www.sns.it/en/concorso-ordinario"
CALL_URL = "https://www.sns.it/en/bando-concorso-ordinario"


class NormaleSuperioreAdapter(OfficialCatalogAdapter):
    university_id = "scuola-normale-superiore"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "normale-superiore"
    institution_name = "Scuola Normale Superiore"
    minimum_expected_programmes = 10
    window_watch_urls = (CATALOG_URL, APPLICATION_URL, CALL_URL)
    retrieval_method = "official-second-level-undergraduate-fields-html"
    catalogue_limitation_reason = (
        "SNS calls its master's-stage offering the second-level undergraduate "
        "course. The competition page says applications are forwarded in July, "
        "but the exact 2026 dates live in the annual call; no month-only wording "
        "is coerced into an application window."
    )

    def __init__(self, minimum_expected_programmes: int = 10) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        policy = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "first or the second level" not in policy
            or "after obtaining a three-years' degree" not in policy
            or "applications can be forwarded in july" not in policy
        ):
            raise ValueError("SNS second-level competition policy is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select(".sns-card__content"):
            faculty_node = card.select_one("h3")
            undergraduate = card.select_one(".sns-grid-column")
            if faculty_node is None or undergraduate is None:
                continue
            faculty = normalise(faculty_node.get_text(" ", strip=True))
            counts: dict[str, list[str]] = {}
            for link in undergraduate.select("a[href*='/corso-ordinario/']"):
                name = normalise(link.get_text(" ", strip=True))
                href = str(link.get("href", ""))
                if name and href:
                    counts.setdefault(name, []).append(href)
            for name, hrefs in counts.items():
                # Humanities and Sciences list first- and second-level versions
                # under the same label. The second occurrence is the master's stage.
                second_level = hrefs[-1]
                if len(hrefs) < 2 and "Political and Social" not in faculty:
                    continue
                rows.append(
                    CatalogEntry(
                        name=f"{name} (second-level undergraduate course)",
                        degree_type="Master-equivalent second level",
                        source_url=urljoin(CATALOG_URL, second_level),
                    )
                )
        return rows
