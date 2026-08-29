from __future__ import annotations

import hashlib
import html as html_lib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredWindow, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.helsinki.fi/sitemap.xml"
APPLICATION_URL = "https://www.helsinki.fi/en/admissions-and-education/apply-bachelors-and-masters-programmes/apply-international-masters-programmes"
INTERNATIONAL_PROGRAMMES_URL = (
    f"{APPLICATION_URL}/explore-our-international-masters-programmes"
)
PATH_RE = re.compile(r"^/en/degree-programmes/[^/]+-masters-programme/?$")
INTERNATIONAL_URL_RE = re.compile(
    r"https://www\.helsinki\.fi/en/degree-programmes/"
    r"[^\s\"'<>]+-masters-programme/?",
    re.I,
)
APPLICATION_PERIOD_RE = re.compile(
    r"studies starting in autumn (?P<intake>20\d{2}) is from\s+"
    r"(?P<opens_day>\d{1,2})\s+to\s+(?P<closes_day>\d{1,2})\s+"
    r"(?P<month>[A-Za-z]+)\s+(?P<year>20\d{2})",
    re.I,
)


class HelsinkiAdapter(OfficialCatalogAdapter):
    university_id = "university-of-helsinki"
    school_prefix = "helsinki"
    institution_name = "University of Helsinki"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 40
    minimum_expected_international_programmes = 30
    retrieval_method = "official-sitemap"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        sitemap_urls = _locations(fetcher(CATALOG_URL))
        entries = []
        for sitemap_url in sitemap_urls:
            entries.extend(self.extract_entries(fetcher(sitemap_url)))
        international_document = fetcher(INTERNATIONAL_PROGRAMMES_URL)
        application_document = fetcher(APPLICATION_URL)
        international_urls = _international_programme_urls(international_document)
        if len(international_urls) < self.minimum_expected_international_programmes:
            raise ValueError(
                "Helsinki's official list only contained "
                f"{len(international_urls)} International Master's programmes; "
                f"expected at least {self.minimum_expected_international_programmes}"
            )

        catalog = self._catalog(entries)
        programme_by_url = {
            _canonical_url(programme.source_url): programme
            for programme in catalog.programmes
        }
        unmatched_urls = sorted(international_urls - set(programme_by_url))
        if unmatched_urls:
            raise ValueError(
                "Helsinki's International Master's list did not match the sitemap "
                f"catalogue: {unmatched_urls[:3]}"
            )

        opens_at, closes_at, intake_year = _application_period(application_document)
        evidence_hash = hashlib.sha256(
            f"{international_document}\n{application_document}".encode()
        ).hexdigest()
        for source_url in international_urls:
            programme = programme_by_url[source_url]
            programme.windows = [
                DiscoveredWindow(
                    round="International Master's application period",
                    opens_at=opens_at,
                    closes_at=closes_at,
                    intake=f"Autumn {intake_year}",
                    source_url=APPLICATION_URL,
                    opens_at_basis="official",
                )
            ]
            programme.deadline_text = (
                "The University of Helsinki's central International Master's "
                f"application period for Autumn {intake_year} runs from "
                f"{opens_at} through {closes_at}."
            )
            programme.parse_status = "parsed"
            programme.retrieval_method = "official-sitemap-and-central-application-page"
            programme.evidence_document_hash = evidence_hash
            programme.admission_route = "direct-master"
        self.intake = f"Autumn {intake_year}"
        return catalog

    def extract_entries(self, xml: str) -> list[CatalogEntry]:
        entries = []
        for source_url in _locations(xml):
            path = urlparse(source_url).path
            if not PATH_RE.fullmatch(path):
                continue
            name = path.rstrip("/").split("/")[-1].removesuffix("-masters-programme")
            entries.append(
                entry(
                    name=f"Master's Programme in {name.replace('-', ' ').title()}",
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _locations(xml: str) -> list[str]:
    return [
        node.text
        for node in ET.fromstring(xml).iter()
        if node.tag.endswith("loc") and node.text
    ]


def _international_programme_urls(document: str) -> set[str]:
    decoded = html_lib.unescape(document).replace("\\/", "/")
    return {
        _canonical_url(match.group(0))
        for match in INTERNATIONAL_URL_RE.finditer(decoded)
    }


def _application_period(document: str) -> tuple[str, str, int]:
    text = " ".join(BeautifulSoup(document, "html.parser").get_text(" ").split())
    match = APPLICATION_PERIOD_RE.search(text)
    if match is None:
        raise ValueError(
            "Helsinki's central page did not contain an exact application period"
        )
    intake_year = int(match.group("intake"))
    year = int(match.group("year"))
    month = datetime.strptime(match.group("month")[:3], "%b").month
    opens_at = datetime(year, month, int(match.group("opens_day"))).date().isoformat()
    closes_at = datetime(year, month, int(match.group("closes_day"))).date().isoformat()
    if intake_year != year or opens_at > closes_at:
        raise ValueError("Helsinki's central application period is inconsistent")
    return opens_at, closes_at, intake_year


def _canonical_url(value: str) -> str:
    parsed = urlparse(value)
    return parsed._replace(
        scheme="https",
        query="",
        fragment="",
        path=parsed.path.rstrip("/"),
    ).geturl()
