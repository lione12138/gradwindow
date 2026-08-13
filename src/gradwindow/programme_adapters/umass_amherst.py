from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://catalognavigator.umass.edu/Catalog/ViewCatalog.aspx?"
    "pageid=viewcatalog&catalogid=75&chapterid=6558&loaduseredits=True"
)
ADMISSIONS_POLICY_URL = (
    "https://catalognavigator.umass.edu/Catalog/ViewCatalog.aspx?"
    "pageid=viewcatalog&catalogid=75&chapterid=6562&topicgroupid=25825"
    "&loaduseredits=True"
)
APPLICATION_URL = "https://www.umass.edu/graduate/apply"


class UMassAmherstAdapter(OfficialCatalogAdapter):
    university_id = "university-of-massachusetts-amherst"
    school_prefix = "umass-amherst"
    institution_name = "University of Massachusetts Amherst"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (ADMISSIONS_POLICY_URL,)
    minimum_expected_programmes = 65
    maximum_expected_programmes = 75
    retrieval_method = "official-graduate-bulletin-master-fields"
    catalogue_limitation_reason = (
        "UMass Amherst's official Graduate Bulletin lists its master's fields, "
        "but states that summer and fall deadlines vary by programme. No shared "
        "exact opening and closing dates are inferred."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 65,
        maximum_expected_programmes: int = 75,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        result = self.parse_catalog(fetcher(CATALOG_URL))
        if len(result.programmes) > self.maximum_expected_programmes:
            raise ValueError(
                f"UMass Amherst bulletin contained {len(result.programmes)} "
                f"master's fields; expected at most "
                f"{self.maximum_expected_programmes}"
            )
        policy = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_POLICY_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "summer/fall entrance cycle, varies by program" not in policy
            or "refer to the academics page" not in policy
        ):
            raise ValueError(
                "UMass Amherst's Graduate Bulletin no longer confirms "
                "programme-specific summer and fall deadlines"
            )
        return result

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        heading = next(
            (
                item
                for item in soup.select(".printcontent h2")
                if "leading to the master" in normalise(item.get_text()).casefold()
            ),
            None,
        )
        if heading is None:
            raise ValueError("UMass Amherst master's fields heading was not found")
        listing = heading.find_next_sibling("p")
        if listing is None:
            raise ValueError("UMass Amherst master's fields list was not found")
        return [
            CatalogEntry(
                name=normalise(link.get_text(" ", strip=True)),
                degree_type="Master",
                source_url=urljoin(CATALOG_URL, str(link["href"])),
            )
            for link in listing.select("a[href]")
        ]
