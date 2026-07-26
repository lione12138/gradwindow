from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "kth-royal-institute-of-technology"
CATALOG_URL = "https://www.kth.se/en/studies/master/programmes"
APPLICATION_URL = "https://www.kth.se/en/studies/master/admissions"


class KTHAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 58) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        if "Submit your application by 15 January" not in fetcher(APPLICATION_URL):
            raise ValueError("KTH official application policy was unavailable")
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = {}
        for link in soup.select('a[href*="/studies/master/"]'):
            name = link.get_text(" ", strip=True)
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            path = urlparse(source_url).path.rstrip("/")
            suffix = path.split("/studies/master/", 1)[-1]
            section = suffix.split("/", 1)[0]
            if not name or section in {"programmes", "admissions", "contact"}:
                continue
            programme_id = f"kth-{_slug(name)}-msc"
            if name == "Computer Science":
                programme_id = "kth-computer-science-msc"
            heading = link.find_previous("h2")
            faculty = heading.get_text(" ", strip=True) if heading else "KTH"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=f"MSc {name}",
                degree_type="MSc",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text="KTH states that 2027 applications open in October and close on 15 January, but no exact October opening date is published. No opening date is inferred.",
                parse_status="no-deadline",
                retrieval_method="official-msc-directory",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"KTH catalogue contained {len(result)} MSc programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
