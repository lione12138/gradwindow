from __future__ import annotations

import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "university-of-technology-sydney"
CATALOG_URL = "https://www.uts.edu.au/sitemap.xml"
APPLICATION_URL = (
    "https://www.uts.edu.au/for-students/admissions-entry/application-dates"
)
EXISTING_INFORMATION_TECHNOLOGY_ID = "uts-information-technology-master"
PATH_RE = re.compile(r"^/courses/(?P<slug>master-of-[^/]+)$", re.I)


class UTSAdapter(BaseProgrammeAdapter):
    """Discover UTS master's courses from the official sitemap."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 90) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        xml = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_sitemap(xml)

    def parse_sitemap(self, xml: str) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for source_url in _locations(xml):
            match = PATH_RE.fullmatch(urlsplit(source_url).path.rstrip("/"))
            if match is None:
                continue
            slug = match.group("slug").lower()
            programme_id = f"uts-{slug}-master"
            if slug == "master-of-information-technology":
                programme_id = EXISTING_INFORMATION_TECHNOLOGY_ID
            programmes[programme_id] = _programme(
                programme_id, _title(slug), source_url
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UTS's official sitemap contained {len(result)} master's "
                f"courses; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _programme(programme_id: str, name: str, source_url: str) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type="Master",
        faculty="University of Technology Sydney",
        department="University of Technology Sydney",
        source_url=source_url,
        application_url=source_url,
        windows=[],
        deadline_text=(
            "UTS's official sitemap confirms this master's course. Session "
            "availability and deadlines vary by course and applicant type; no "
            "exact opening-and-closing pair is inferred."
        ),
        parse_status="no-deadline",
        retrieval_method="official-sitemap",
        evidence_quality="official-full-text",
    )


def _locations(xml: str) -> list[str]:
    return [
        str(node.text or "").strip()
        for node in ElementTree.fromstring(xml).iter()
        if node.tag.rsplit("}", 1)[-1].lower() == "loc" and (node.text or "").strip()
    ]


def _title(slug: str) -> str:
    words = [word.capitalize() for word in slug.split("-")]
    acronyms = {"It": "IT", "Mba": "MBA", "Of": "of", "Tesol": "TESOL"}
    return " ".join(acronyms.get(word, word) for word in words)
