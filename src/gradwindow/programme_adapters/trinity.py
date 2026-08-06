from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.maths.tcd.ie/postgraduate/"


class TrinityAdapter(BaseProgrammeAdapter):
    university_id = "trinity-college-dublin-the-university-of-dublin"
    catalog_url = CATALOG_URL
    application_url = CATALOG_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 3

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for heading in soup.select("h2"):
            title = normalise(heading.get_text(" ", strip=True))
            if not title.startswith("M.Sc."):
                continue
            link = heading.find_next("a", href=True)
            if link is None:
                continue
            name = (
                "Mathematics by Research (M.Sc.)"
                if "Ph.D. by research" in title
                else title
            )
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            programme_id = f"trinity-mathematics-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="M.Sc.",
                faculty="Faculty of Science, Technology, Engineering and Mathematics",
                department="School of Mathematics",
                source_url=source_url,
                application_url=CATALOG_URL,
                windows=[],
                deadline_text=(
                    "Trinity's official School of Mathematics directory lists this "
                    "M.Sc. route. This adapter currently covers the mathematics "
                    "school because the central course finder returns an AWS WAF "
                    "challenge to the monitor. No complete exact opening-and-closing "
                    "pair is published on the checked school page, so no dates are "
                    "inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-trinity-mathematics-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda programme: programme.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Trinity Mathematics' official directory contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
