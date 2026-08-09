from __future__ import annotations

from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.hu-berlin.de/sitemap.xml"
APPLICATION_URL = (
    "https://www.hu-berlin.de/en/studies/admission/enrolment-office/"
    "enrollment-office/leave-of-absence-1/leave-of-absence"
)
MASTER_MARKERS = (
    ("-master-of-education-", "MEd"),
    ("-master-of-science-", "MSc"),
    ("-master-of-arts-", "MA"),
    ("-master-of-laws-", "LLM"),
    ("-master-of-", "Master"),
)


class HumboldtAdapter(OfficialCatalogAdapter):
    university_id = "humboldt-universit-t-zu-berlin"
    school_prefix = "humboldt"
    institution_name = "Humboldt-Universität zu Berlin"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 140
    retrieval_method = "official-study-finder-sitemap"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index = BeautifulSoup(fetcher(CATALOG_URL), "xml")
        study_sitemaps = [
            _compact_url(node.get_text())
            for node in index.select("loc")
            if "sitemap=study_finder" in node.get_text()
        ]
        if not study_sitemaps:
            raise ValueError("Humboldt sitemap did not expose the study finder sitemap")
        return self.parse_catalog(fetcher(study_sitemaps[0]))

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "xml")
        entries: list[CatalogEntry] = []
        for node in soup.select("loc"):
            source_url = _compact_url(node.get_text())
            parsed = _programme_from_url(source_url)
            if parsed is None:
                continue
            name, degree_type = parsed
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_type,
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _programme_from_url(source_url: str) -> tuple[str, str] | None:
    slug = unquote(urlsplit(source_url).path.rstrip("/").rsplit("/", 1)[-1])
    for marker, degree_type in MASTER_MARKERS:
        if marker not in slug:
            continue
        subject, qualifier = slug.split(marker, 1)
        qualifier = qualifier.removesuffix("-hauptfach").strip("-")
        if qualifier == "hauptfach":
            qualifier = ""
        name = _humanise(subject)
        if qualifier:
            name = f"{name} — {_humanise(qualifier)}"
        return name, degree_type
    return None


def _humanise(value: str) -> str:
    return " ".join(value.replace("-", " ").split()).title()


def _compact_url(value: str) -> str:
    return "".join(value.split())
