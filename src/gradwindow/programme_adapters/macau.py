from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from .base import DiscoveredCatalog, DiscoveredWindow
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://grs.um.edu.mo/index.php/prospective-students/"
    "master-postgraduate-certificate-diploma-programmes/"
)
APPLICATION_URL = CATALOG_URL
WINDOW_RE = re.compile(
    r"(?P<opens>\d{1,2}\s+[A-Za-z]+\s+20\d{2})\s*[–—-]\s*"
    r"(?P<closes>\d{1,2}\s+[A-Za-z]+\s+20\d{2})\s*"
    r"\((?P<round>[^)]+)\)",
    re.IGNORECASE,
)
INTAKE_RE = re.compile(r"Academic Year\s+(?P<intake>20\d{2}/20\d{2})", re.I)
NON_MASTER_PROGRAMMES = {
    "Pre-Primary Education",
    "Primary Education",
    "Secondary Education",
}


class MacauAdapter(OfficialCatalogAdapter):
    university_id = "university-of-macau"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "macau"
    institution_name = "University of Macau"
    minimum_expected_programmes = 60
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-graduate-admissions-table"
    catalogue_limitation_reason = (
        "Macau's official central admissions table enumerates current master's "
        "programmes and common application batches. Programme exceptions remain "
        "monitored on the same first-party page."
    )

    def __init__(self, minimum_expected_programmes: int = 60) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        catalog = self._catalog(self.extract_entries(html))
        soup = BeautifulSoup(html, "html.parser")
        page_text = normalise(soup.get_text(" ", strip=True))
        intake_match = INTAKE_RE.search(page_text)
        window_matches = list(WINDOW_RE.finditer(page_text))
        if intake_match is None or len(window_matches) < 2:
            raise ValueError("Macau's official application batch dates are missing")
        intake = f"{intake_match.group('intake')} academic year"
        windows = [
            DiscoveredWindow(
                round=normalise(match.group("round")),
                opens_at=_iso_date(match.group("opens")),
                closes_at=_iso_date(match.group("closes")),
                intake=intake,
                source_url=CATALOG_URL,
                opens_at_basis="official",
            )
            for match in window_matches[:2]
        ]
        deadline_text = (
            "Official University of Macau admissions table publishes "
            f"{len(windows)} exact application batches for {intake}."
        )
        return DiscoveredCatalog(
            application_opens_at=windows[0].opens_at,
            programmes=[
                replace(
                    programme,
                    windows=windows,
                    deadline_text=deadline_text,
                    parse_status="parsed",
                )
                for programme in catalog.programmes
            ],
        )

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        seen: set[tuple[str, str, str]] = set()

        def add(name: str, degree_type: str, source_url: str) -> None:
            name = normalise(name)
            if name in NON_MASTER_PROGRAMMES:
                return
            key = (name, normalise(degree_type), source_url)
            if key in seen:
                return
            seen.add(key)
            rows.append(
                CatalogEntry(
                    name=key[0],
                    degree_type=key[1],
                    source_url=key[2],
                )
            )

        for table_row in soup.select("table tr"):
            cells = table_row.find_all("td", recursive=False)
            if len(cells) < 2:
                continue
            programme_cell = cells[1]
            for listing in programme_cell.find_all("ul", recursive=False):
                degree_type = _preceding_degree(listing)
                for item in listing.find_all("li", recursive=False):
                    links_by_url: dict[str, list[str]] = {}
                    for link in item.select("a[href]"):
                        source_url = str(link["href"]).rstrip("/")
                        if not _is_macau_url(source_url):
                            continue
                        label = normalise(link.get_text(" ", strip=True))
                        labels = links_by_url.setdefault(source_url, [])
                        if label and label not in labels:
                            labels.append(label)
                    for source_url, labels in links_by_url.items():
                        label = (
                            normalise(item.get_text(" ", strip=True))
                            if len(links_by_url) == 1
                            else normalise(" ".join(labels))
                        )
                        add(label, degree_type, source_url)
            for link in programme_cell.select("a[href]"):
                if link.find_parent("ul") is not None:
                    continue
                source_url = str(link["href"]).rstrip("/")
                label = normalise(link.get_text(" ", strip=True))
                if not _is_macau_url(source_url) or "master" not in label.casefold():
                    continue
                parent_text = normalise(link.parent.get_text(" ", strip=True))
                if label.casefold().endswith(" in") and parent_text.startswith(label):
                    label = parent_text
                add(label, "Master", source_url)
        return rows


def _preceding_degree(listing: Tag) -> str:
    sibling = listing.previous_sibling
    while sibling is not None:
        value = normalise(
            sibling.get_text(" ", strip=True)
            if isinstance(sibling, Tag)
            else str(sibling)
        )
        if "master" in value.casefold():
            return value
        sibling = sibling.previous_sibling
    return "Master"


def _is_macau_url(value: str) -> bool:
    hostname = (urlparse(value).hostname or "").casefold()
    return hostname == "um.edu.mo" or hostname.endswith(".um.edu.mo")


def _iso_date(value: str) -> str:
    return datetime.strptime(normalise(value), "%d %B %Y").date().isoformat()
