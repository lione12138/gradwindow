from __future__ import annotations

import json
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "the-university-of-warwick"
CATALOG_URL = "https://warwick.ac.uk/study/postgraduate/courses/"
APPLICATION_URL = "https://warwick.ac.uk/study/postgraduate/apply/"
API_URL = (
    "https://sitebuilder.warwick.ac.uk/sitebuilder2/api/dataentry/entries.json"
    "?page=%2Fstudy%2Fpostgraduate%2Fcourses%2Fcourse-list"
)
EXISTING_CS_ID = "warwick-computer-science-msc"
_DEGREE_RE = re.compile(
    r"\((MSc|MA|LLM|MRes|MPH|MBA|MEd|MFA|MPA|MMath|MASc|MMedEd)\)\s*$"
)


class WarwickAdapter(BaseProgrammeAdapter):
    """Discover Warwick's centrally listed postgraduate taught master's courses."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by course"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 110) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue_html = fetcher(CATALOG_URL)
        application_html = fetcher(APPLICATION_URL)
        application_text = _normalise(
            BeautifulSoup(application_html, "html.parser").get_text(" ", strip=True)
        ).lower()
        required_phrases = ("applications for most courses", "on-time deadline")
        if not all(phrase in application_text for phrase in required_phrases):
            raise ValueError(
                "Warwick's official application policy could not be verified"
            )
        if BeautifulSoup(catalogue_html, "html.parser").select_one("#course-container"):
            return self.parse_json(fetcher(API_URL))
        return self.parse_catalog(catalogue_html)

    def parse_json(self, payload: str) -> DiscoveredCatalog:
        rows = []
        for item in json.loads(payload)["items"]:
            categories = [
                c if isinstance(c, str) else c.get("name", "")
                for c in item.get("categories", [])
            ]
            if "Visibility: Hidden" in categories or not any(
                c.startswith("Study level: Postgraduate Taught") for c in categories
            ):
                continue
            card = BeautifulSoup(item.get("parsedContentBody", ""), "html.parser")
            link = card.select_one("h3 a[href]")
            qualification = card.select_one(".qualification")
            if link is None or qualification is None:
                continue
            degree_text = _normalise(qualification.get_text(" ", strip=True))
            degree = _DEGREE_RE.search(degree_text)
            if not degree or not degree_text.startswith("Master of "):
                continue
            name = _normalise(link.get_text(" ", strip=True))
            name = re.sub(
                rf"\s+\(?{re.escape(degree.group(1))}"
                r"(?:\s*/\s*(?:PGDip|PGCert))*\)?$",
                "",
                name,
            ).strip()
            rows.append(
                (f"{name} ({degree.group(1)})", urljoin(CATALOG_URL, link["href"]))
            )
        return self._catalogue(rows)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for item in soup.select(".feed-item-list-item"):
            if "postgraduate taught" not in item.get_text(" ", strip=True).lower():
                continue
            link = item.select_one(
                '.feed-item-abstract a[href*="/study/postgraduate/courses/"]'
            )
            if link is None:
                continue
            rows.append(
                (_normalise(link.get_text(" ", strip=True)), str(link.get("href", "")))
            )
        return self._catalogue(rows)

    def _catalogue(self, rows: list[tuple[str, str]]) -> DiscoveredCatalog:
        programmes_by_url = {}
        for name, source_url in rows:
            degree_match = _DEGREE_RE.search(name)
            if degree_match is None or not _is_official(source_url):
                continue
            degree_type = degree_match.group(1)
            plain_name = _DEGREE_RE.sub("", name).strip()
            programme_id = f"warwick-{_slugify(plain_name)}-{degree_type.lower()}"
            if plain_name == "Computer Science" and degree_type == "MSc":
                programme_id = EXISTING_CS_ID
            programmes_by_url[source_url] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty="University of Warwick",
                department="University of Warwick",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Warwick's official application page confirms that applications "
                    "are open and publishes an on-time closing date for the current "
                    "cycle, but it does not state the exact opening date. The course "
                    "therefore remains monitored and no opening date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-postgraduate-course-directory",
                evidence_quality="official-full-text",
            )
        programmes = sorted(programmes_by_url.values(), key=lambda item: item.name)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "Warwick's official postgraduate directory only contained "
                f"{len(programmes)} taught master's courses; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _is_official(value: str) -> bool:
    host = (urlparse(value).hostname or "").lower()
    return host == "warwick.ac.uk" or host.endswith(".warwick.ac.uk")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
