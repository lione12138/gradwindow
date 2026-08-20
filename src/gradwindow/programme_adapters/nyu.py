from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://bulletins.nyu.edu/programs/"
APPLICATION_URL = "https://www.nyu.edu/admissions/graduate-admissions.html"


class NYUAdapter(BaseProgrammeAdapter):
    university_id = "new-york-university-nyu"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 225

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in soup.select("li.item"):
            link = item.select_one("a[href]")
            title = item.select_one(".item-container .title")
            keywords = [
                normalise(keyword.get_text(" ", strip=True))
                for keyword in item.select(".item-container .keyword")
            ]
            if (
                link is None
                or title is None
                or "Masters" not in keywords
                or "Graduate" not in keywords
            ):
                continue
            name = normalise(title.get_text(" ", strip=True))
            degree_type = keywords[0] if keywords else "Master"
            graduate_index = keywords.index("Graduate")
            faculty = (
                keywords[graduate_index + 1]
                if graduate_index + 1 < len(keywords)
                else "New York University"
            )
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            if not name or not source_url.startswith("https://bulletins.nyu.edu/"):
                continue
            programme_id = f"nyu-{slug(faculty)}-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "NYU's official university-wide Program Finder classifies this "
                    f"as a graduate master's route in {faculty}. Admissions are "
                    "managed by the relevant NYU school and no complete universal "
                    "exact opening-and-closing pair is published, so no dates are "
                    "inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-nyu-program-finder",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda programme: programme.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "NYU's official Program Finder contained "
                f"{len(result)} master's routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
