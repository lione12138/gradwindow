from __future__ import annotations

import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "adelaide-university"
CATALOG_URL = "https://adelaide.edu.au/sitemap.xml"
APPLICATION_URL = "https://adelaide.edu.au/study/international-students/how-to-apply/"
EXISTING_COMPUTER_SCIENCE_ID = "adelaide-computer-science-master"
PATH_RE = re.compile(r"^/study/degrees/(?:online/)?(?P<slug>master-of-[^/]+)/?$", re.I)


class AdelaideAdapter(BaseProgrammeAdapter):
    """Discover Adelaide University master's degrees from its official sitemap."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 100) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        xml = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_sitemap(xml)

    def parse_sitemap(self, xml: str) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for source_url in _locations(xml):
            path = urlsplit(source_url).path
            match = PATH_RE.fullmatch(path)
            if match is None:
                continue
            slug = match.group("slug").lower()
            online = path.lower().startswith("/study/degrees/online/")
            delivery_prefix = "online-" if online else ""
            programme_id = f"adelaide-{delivery_prefix}{slug}-master"
            if slug == "master-of-computer-science" and not online:
                programme_id = EXISTING_COMPUTER_SCIENCE_ID
            programmes[programme_id] = _programme(
                programme_id,
                f"{_title(slug)} (Online)" if online else _title(slug),
                source_url,
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Adelaide University's official sitemap contained "
                f"{len(result)} master's degrees; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _programme(programme_id: str, name: str, source_url: str) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type="Master",
        faculty="Adelaide University",
        department="Adelaide University",
        source_url=source_url,
        application_url=source_url,
        windows=[],
        deadline_text=(
            "Adelaide University's official sitemap confirms this master's "
            "degree. Intake availability and closing dates vary by degree; no "
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
    replacements = {"Mba": "MBA", "Of": "of"}
    return " ".join(replacements.get(word, word) for word in words)
