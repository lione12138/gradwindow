from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://international.tau.ac.il/fees_and_expenses?tab=3"
APPLICATION_URL = "https://international.tau.ac.il/Degree_Programs"
DEGREE_RE = re.compile(r"\b(MA|MDM|MBA|MFA|MMus|LLM|MSc)\b", re.IGNORECASE)


class TelAvivAdapter(OfficialCatalogAdapter):
    university_id = "tel-aviv-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "tel-aviv"
    institution_name = "Tel Aviv University"
    minimum_expected_programmes = 21
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-graduate-fee-table"
    catalogue_limitation_reason = (
        "Tel Aviv University's official international fee table enumerates the "
        "international graduate degrees covered by that fee table and links to "
        "their programme pages; it is not the complete university catalogue. "
        "Programme-specific exact application windows are not "
        "published in that central table."
    )

    def __init__(self, minimum_expected_programmes: int = 21) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        tables = [
            table
            for table in soup.select("table")
            if any(
                normalise(cell.get_text(" ", strip=True)).casefold()
                == "graduate degrees"
                for cell in table.select("tr:first-child th, tr:first-child td")
            )
        ]
        if len(tables) != 1:
            raise ValueError(
                "Tel Aviv graduate degree fee table is missing or ambiguous"
            )
        rows: list[CatalogEntry] = []
        for table_row in tables[0].select("tr"):
            cell = table_row.find(["td", "th"])
            if cell is None:
                continue
            row_text = normalise(cell.get_text(" ", strip=True))
            degree_match = DEGREE_RE.search(row_text)
            if degree_match is None:
                continue
            link = cell.select_one("a[href]")
            if link is None or not normalise(link.get_text(" ", strip=True)):
                raise ValueError(
                    "Tel Aviv graduate degree row is missing its programme link"
                )
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            host = urlparse(source_url).hostname or ""
            if urlparse(source_url).scheme not in {"https", "http"} or not (
                host == "tau.ac.il" or host.endswith(".tau.ac.il")
            ):
                raise ValueError(
                    "Tel Aviv programme link is not an official university URL"
                )
            rows.append(
                CatalogEntry(
                    name=normalise(link.get_text(" ", strip=True)),
                    degree_type=degree_match.group(1),
                    source_url=source_url,
                )
            )
        return rows
