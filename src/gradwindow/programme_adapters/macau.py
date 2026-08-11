from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from .base import DiscoveredCatalog, DiscoveredWindow
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise, slug

CATALOG_URL = (
    "https://grs.um.edu.mo/index.php/prospective-students/"
    "master-postgraduate-certificate-diploma-programmes/"
)
CHINESE_CATALOG_URL = (
    "https://grs.um.edu.mo/index.php/prospective-student/"
    "master-postgraduate-certificate-diploma-programmes/?lang=zh-hant"
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
CHINESE_MASTER_RE = re.compile(r"[硕碩]士")


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


def parse_official_chinese_translations(
    english_html: str, chinese_html: str
) -> dict[str, str]:
    """Match the mirrored official catalogues without guessing translations."""

    english_soup = BeautifulSoup(english_html, "html.parser")
    chinese_soup = BeautifulSoup(chinese_html, "html.parser")
    english_table = _programme_table(english_soup)
    chinese_table = _programme_table(chinese_soup)
    english_rows = english_table.select("tr")
    chinese_rows = chinese_table.select("tr")
    if len(english_rows) != len(chinese_rows):
        raise ValueError("Macau's English and Chinese programme tables diverged")

    adapter = MacauAdapter(minimum_expected_programmes=1)
    translations: dict[str, str] = {}
    for english_row, chinese_row in zip(english_rows, chinese_rows, strict=True):
        english_cells = english_row.find_all("td", recursive=False)
        chinese_cells = chinese_row.find_all("td", recursive=False)
        if len(english_cells) < 2:
            continue
        if len(chinese_cells) < 2:
            raise ValueError("Macau's Chinese programme row is missing a label cell")
        entries = adapter.extract_entries(f"<table>{english_row}</table>")
        if not entries:
            continue
        labels = _translated_row_labels(english_cells[1], chinese_cells[1])
        if len(entries) != len(labels):
            faculty = normalise(english_cells[0].get_text(" ", strip=True))
            raise ValueError(
                "Macau's official Chinese catalogue did not align with "
                f"{faculty}: {len(entries)} English and {len(labels)} Chinese labels"
            )
        for entry, label in zip(entries, labels, strict=True):
            programme_id = f"macau-{slug(entry.name)}-{slug(entry.degree_type)}"
            translations[programme_id] = label

    expected_ids = {
        f"macau-{slug(entry.name)}-{slug(entry.degree_type)}"
        for entry in adapter.extract_entries(english_html)
    }
    if translations.keys() != expected_ids:
        missing = sorted(expected_ids - translations.keys())
        raise ValueError(
            "Macau's official Chinese catalogue translation coverage is incomplete: "
            + ", ".join(missing[:5])
        )
    return translations


def _programme_table(soup: BeautifulSoup) -> Tag:
    tables = soup.select("table")
    if not tables:
        raise ValueError("Macau's official programme table is missing")
    table = max(tables, key=lambda item: len(item.select("a[href]")))
    if not table.select("a[href]"):
        raise ValueError("Macau's official programme table contains no links")
    return table


def _translated_row_labels(english_cell: Tag, chinese_cell: Tag) -> list[str]:
    english_lists = english_cell.find_all("ul", recursive=False)
    chinese_lists = chinese_cell.find_all("ul", recursive=False)
    if len(english_lists) != len(chinese_lists):
        raise ValueError("Macau's English and Chinese programme lists diverged")

    labels: list[str] = []
    for english_list, chinese_list in zip(english_lists, chinese_lists, strict=True):
        english_items = [
            item
            for item in _listing_items(english_list)
            if item[0] not in NON_MASTER_PROGRAMMES
        ]
        chinese_items = _listing_items(chinese_list)
        if not english_items:
            continue
        if len(english_items) != len(chinese_items):
            raise ValueError("Macau's translated programme list changed order or size")
        labels.extend(label for label, _ in chinese_items)

    english_direct = _direct_master_items(english_cell, chinese=False)
    chinese_direct = _direct_master_items(chinese_cell, chinese=True)
    if len(english_direct) != len(chinese_direct):
        raise ValueError("Macau's translated direct programme links diverged")
    labels.extend(label for label, _ in chinese_direct)
    if any(not re.search(r"[\u3400-\u9fff]", label) for label in labels):
        raise ValueError(
            "Macau's official Chinese catalogue returned a non-Chinese label"
        )
    return labels


def _listing_items(listing: Tag) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
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
        for source_url, link_labels in links_by_url.items():
            label = (
                normalise(item.get_text(" ", strip=True))
                if len(links_by_url) == 1
                else normalise(" ".join(link_labels))
            )
            rows.append((label, source_url))
    return rows


def _direct_master_items(cell: Tag, *, chinese: bool) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen_groups: set[tuple[int, str]] = set()
    seen_rows: set[tuple[str, str]] = set()
    for link in cell.select("a[href]"):
        if link.find_parent("ul") is not None:
            continue
        source_url = str(link["href"]).rstrip("/")
        if not _is_macau_url(source_url):
            continue
        parent = link.parent
        if not isinstance(parent, Tag):
            continue
        group_key = (id(parent), source_url)
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        matching_links = [
            candidate
            for candidate in parent.select("a[href]")
            if candidate.find_parent("ul") is None
            and str(candidate.get("href", "")).rstrip("/") == source_url
        ]
        label = normalise(
            parent.get_text(" ", strip=True)
            if len(matching_links) > 1
            else link.get_text(" ", strip=True)
        )
        is_master = (
            bool(CHINESE_MASTER_RE.search(label))
            if chinese
            else ("master" in label.casefold())
        )
        row = (label, source_url)
        if is_master and row not in seen_rows:
            seen_rows.add(row)
            rows.append(row)
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
