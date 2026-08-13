from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://apply.unimi.it/institutions/institution/1-university-milan"
APPLICATION_URL = CATALOG_URL
_VISA_SUFFIX_RE = re.compile(r"\s*\(FOR VISA APPLICANTS\)\s*$", re.IGNORECASE)


class MilanAdapter:
    university_id = "university-of-milan"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    catalogue_status = "partial"
    retrieval_method = "official-international-application-portal"
    catalogue_limitation_reason = (
        "The official international application portal exposes the master's "
        "programmes accepting applications through that route, not the complete "
        "University of Milan catalogue. Deadlines vary by programme and applicant "
        "category, so no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 25) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher) -> DiscoveredCatalog:
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in soup.select("div.item"):
            link = item.select_one("a[href*='/courses/course/']")
            text = normalise(item.get_text(" ", strip=True))
            if link is None or "Master's (Laurea magistrale)" not in text:
                continue
            label = link.select_one("span.awards.label")
            label_text = normalise(label.get_text(" ", strip=True)) if label else ""
            name = normalise(link.get_text(" ", strip=True))
            if label_text and name.startswith(label_text):
                name = name[len(label_text) :].strip()
            name = _VISA_SUFFIX_RE.sub("", name).strip()
            if not name:
                continue
            details = [
                normalise(node.get_text(" ", strip=True))
                for node in item.select("small div.item")
            ]
            faculty = next(
                (value for value in details if "master's" not in value.casefold()),
                "University of Milan",
            )
            programme_id = f"milan-{slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master's (Laurea magistrale)",
                faculty=faculty,
                department=faculty,
                source_url=urljoin(CATALOG_URL, str(link.get("href", ""))),
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme is listed in the University of Milan's official "
                    "international application portal. Exact dates vary by route, "
                    "so no application window is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Milan portal contained {len(result)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
