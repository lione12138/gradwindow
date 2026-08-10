from __future__ import annotations

from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://gpadmissions.osu.edu/programs/"
ADMISSIONS_URL = (
    "https://gradsch.osu.edu/graduate-school-handbook-gsh/gsh-section-2-admissions"
)
APPLICATION_URL = "https://gpadmissions.osu.edu/grad/apply-online.html"


class OhioStateAdapter(BaseProgrammeAdapter):
    university_id = "ohio-state-university"
    catalog_url = CATALOG_URL
    admissions_url = ADMISSIONS_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-graduate-programme-search"
    catalogue_limitation_reason = (
        "Ohio State says its graduate application process opens near the beginning "
        "of autumn semester and deadlines vary by programme. The policy has no "
        "cycle-specific exact opening date, so programme pages remain monitored."
    )

    def __init__(self, minimum_expected_programmes: int = 135) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue = self.parse_catalog(fetcher(CATALOG_URL))
        policy = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "application process opens at the beginning of autumn semester"
            not in policy
        ):
            raise ValueError("Ohio State's official graduate opening policy is missing")
        if "deadlines for receiving applications may vary" not in policy:
            raise ValueError(
                "Ohio State's programme-specific deadline policy is missing"
            )
        return catalogue

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select('a[href*="program.aspx?prog="]'):
            label = normalise(link.get_text(" ", strip=True))
            if "master" not in label.casefold() or " - " not in label:
                continue
            name, degree_type = (part.strip() for part in label.rsplit(" - ", 1))
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            source_id = parse_qs(urlparse(source_url).query).get("prog", [""])[0]
            programme_id = f"ohio-state-{source_id or slug(label)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty="The Ohio State University Graduate School",
                department="The Ohio State University Graduate School",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in Ohio State's official graduate programme "
                    "search. Exact deadlines vary by programme and the central "
                    "opening policy is not cycle-specific, so no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Ohio State catalogue contained {len(result)} master's routes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
