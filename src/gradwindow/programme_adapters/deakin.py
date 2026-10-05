from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://handbook.deakin.edu.au/courses-search/allcourses.php"
APPLICATION_URL = "https://www.deakin.edu.au/study/how-to-apply"


class DeakinAdapter(OfficialCatalogAdapter):
    university_id = "deakin-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "deakin"
    institution_name = "Deakin University"
    minimum_expected_programmes = 85
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-current-course-handbook"
    catalogue_limitation_reason = (
        "Deakin's official course handbook identifies current coursework and "
        "research master's course versions. Intakes and application timing vary "
        "by course and applicant category, so no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 85) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        entries = self.extract_entries(html)
        seen = {item.name for item in entries}
        soup = BeautifulSoup(html, "html.parser")
        for table in soup.select("table")[2:4]:
            for row in table.select("tr"):
                link = row.select_one("a[href]")
                if link is None:
                    continue
                name = normalise(link.get_text(" ", strip=True))
                if (
                    not name.startswith(("Master ", "Executive Master "))
                    or name in seen
                ):
                    continue
                # A stated end year is not a missing note. Only investigate
                # catalogue rows whose commencement guidance is absent.
                if "commenced" in row.get_text(" ", strip=True).casefold():
                    continue
                url = urljoin(CATALOG_URL, str(link["href"]))
                parsed = urlsplit(url)
                query = parse_qs(parsed.query)
                code = query.get("course", [""])[0]
                version = query.get("version", [""])[0]
                if (
                    parsed.hostname != "handbook.deakin.edu.au"
                    or not code
                    or not version
                ):
                    continue
                detail = BeautifulSoup(fetcher(url), "html.parser")
                fields = {}
                for detail_row in detail.select("tr"):
                    label, value = detail_row.find("th"), detail_row.find("td")
                    if label is not None and value is not None:
                        fields[normalise(label.get_text()).casefold()] = normalise(
                            value.get_text(" ", strip=True)
                        )
                if (
                    fields.get("deakin course code") != code
                    or fields.get("course version") != version
                    or not re.fullmatch(
                        r"For students who commenced from 20\d{2} onwards\.?",
                        fields.get("course information", ""),
                        re.I,
                    )
                ):
                    continue
                entries.append(
                    CatalogEntry(name=name, degree_type="Master", source_url=url)
                )
                seen.add(name)
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        if len(tables) < 4:
            return []
        rows: list[CatalogEntry] = []
        seen: set[str] = set()
        for table in (tables[2], tables[3]):
            for table_row in table.select("tr"):
                link = table_row.select_one("a[href]")
                if link is None:
                    continue
                name = normalise(link.get_text(" ", strip=True))
                row_text = normalise(table_row.get_text(" ", strip=True))
                if not name.startswith(("Master ", "Executive Master ")):
                    continue
                if "onwards" not in row_text.casefold() or name in seen:
                    continue
                seen.add(name)
                rows.append(
                    CatalogEntry(
                        name=name,
                        degree_type="Master",
                        source_url=urljoin(CATALOG_URL, str(link["href"])),
                    )
                )
        return rows
