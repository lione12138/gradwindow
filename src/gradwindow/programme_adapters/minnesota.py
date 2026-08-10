from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://apps.grad.umn.edu/programs/selector.aspx"
APPLICATION_URL = "https://choose.umn.edu/apply/"
_MASTER_SUFFIX_RE = re.compile(
    r"(?P<degree>M\.Acc\.|M(?:S)?(?:\s+[A-Z][A-Za-z.]*)+)"
    r"(?:\s+\([^)]*\)|\s+Major)?$"
)
_DOCTORAL_RE = re.compile(r"\b(?:Ph D|D M A|D B A|D N P|S J D|Au D|O T D|Ed D|D P T)\b")


class MinnesotaAdapter(BaseProgrammeAdapter):
    university_id = "university-of-minnesota-twin-cities"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-graduate-program-selector"
    catalogue_limitation_reason = (
        "The official programme selector does not publish a universal pair of "
        "application opening and closing dates; deadlines remain programme-specific."
    )

    def __init__(self, minimum_expected_programmes: int = 180) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select('a[href*="at_a_glance.aspx"]'):
            name = normalise(link.get_text(" ", strip=True))
            if not name or "(Duluth)" in name or _DOCTORAL_RE.search(name):
                continue
            match = _MASTER_SUFFIX_RE.search(name)
            if match is None and not name.startswith("Master of "):
                continue
            degree_type = (
                normalise(match.group("degree")) if match else "Master of Science"
            )
            source_url = urljoin(CATALOG_URL, link["href"])
            programme_id = f"minnesota-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty="University of Minnesota Graduate School",
                department="University of Minnesota Graduate School",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in the official University of Minnesota "
                    "graduate-program selector. The selector does not publish an "
                    "official exact opening-and-closing pair, so no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Minnesota selector contained {len(result)} Twin Cities master's "
                f"routes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
