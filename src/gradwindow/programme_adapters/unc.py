from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://catalog.unc.edu/graduate/degree-programs/"
APPLICATION_URL = "https://gradschool.unc.edu/admissions/"

_MASTER_DEGREE_RE = re.compile(
    r"(?<![A-Za-z])M(?:\.[A-Z])+\.?|(?<![A-Za-z])M[A-Z]{1,6}(?![A-Za-z])"
)


class UNCAdapter(BaseProgrammeAdapter):
    university_id = "university-of-north-carolina-chapel-hill"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 100

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one("#byorgtextcontainer")
        if container is None:
            raise ValueError("UNC's official degree-program catalogue is missing")

        hierarchy: dict[int, str] = {}
        programmes: dict[str, DiscoveredProgramme] = {}
        for paragraph in container.find_all("p", recursive=False):
            text = normalise(paragraph.get_text(" ", strip=True))
            label_match = re.match(r"^(.*?)\s+(?:\u2013|-)\s*", text)
            if label_match is None:
                continue
            margin = re.search(r"margin-left:\s*(\d+)px", paragraph.get("style", ""))
            level = int(margin.group(1)) // 40 if margin is not None else 0
            hierarchy[level] = normalise(label_match.group(1))
            hierarchy = {key: value for key, value in hierarchy.items() if key <= level}
            if "not active" in text.casefold():
                continue

            names = []
            for key in sorted(hierarchy):
                value = hierarchy[key]
                if not names or names[-1].casefold() != value.casefold():
                    names.append(value)
            name = ": ".join(names)
            for link in paragraph.select("a[href]"):
                for degree_type in _MASTER_DEGREE_RE.findall(
                    normalise(link.get_text(" ", strip=True)).upper()
                ):
                    programme_id = f"unc-{slug(name)}-{slug(degree_type)}"
                    programmes[programme_id] = DiscoveredProgramme(
                        id=programme_id,
                        name=name,
                        degree_type=degree_type,
                        faculty="The Graduate School",
                        department=name.split(":", 1)[0],
                        source_url=CATALOG_URL,
                        application_url=APPLICATION_URL,
                        windows=[],
                        deadline_text=(
                            "UNC-Chapel Hill's official graduate catalogue lists "
                            f"this {degree_type} route. Deadlines and opening dates "
                            "are maintained by the individual programmes, and no "
                            "complete central exact date pair is published, so no "
                            "dates are inferred."
                        ),
                        parse_status="no-deadline",
                        retrieval_method="official-graduate-degree-catalogue",
                        evidence_quality="official-full-text",
                    )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "UNC's official catalogue contained "
                f"{len(result)} master's degree routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
