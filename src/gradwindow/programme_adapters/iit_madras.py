from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://mtechadm.iitm.ac.in/"
APPLICATION_URL = CATALOG_URL


class IITMadrasAdapter(OfficialCatalogAdapter):
    university_id = "indian-institute-of-technology-madras-iitm"
    school_prefix = "iitm"
    institution_name = "Indian Institute of Technology Madras"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 30
    retrieval_method = "official-2026-mtech-ma-msc-admissions-catalogue"

    def _catalog(self, entries: list[CatalogEntry]):
        catalog = super()._catalog(entries)
        for programme in catalog.programmes:
            if programme.name == "M.Tech in Computer Science and Engineering":
                programme.id = "iitm-mtech-computer-science-engineering"
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for table in soup.select("table"):
            heading = table.find_previous("h2")
            heading_text = heading.get_text(" ", strip=True) if heading else ""
            if heading_text.startswith("M.Tech"):
                entries.extend(self._programme_rows(table, "M.Tech"))
            elif heading_text.startswith("M.A."):
                entries.extend(self._programme_rows(table, "MA"))
            elif heading_text.startswith("M.Sc.") and table.select_one("th"):
                entries.extend(self._msc_rows(table))
        return entries

    def _programme_rows(self, table: Tag, degree_type: str) -> list[CatalogEntry]:
        result: list[CatalogEntry] = []
        department = self.institution_name
        source_url = CATALOG_URL
        for row in table.select("tr"):
            if "department-row" in row.get("class", []):
                title = row.select_one(".dept-title")
                link = row.select_one("a[href]")
                if title:
                    department = normalise(title.get_text(" ", strip=True))
                if link:
                    source_url = str(link["href"])
                continue
            if "program-row" not in row.get("class", []):
                continue
            for badge in row.select(".badge"):
                badge.decompose()
            name = re.sub(
                r"\s+NEW$", "", normalise(row.get_text(" ", strip=True))
            ).strip()
            if name.startswith("Stream:"):
                name = f"{department} — {name}"
            result.append(
                entry(
                    name=name,
                    degree_type=degree_type,
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return result

    def _msc_rows(self, table: Tag) -> list[CatalogEntry]:
        result: list[CatalogEntry] = []
        for row in table.select("tr"):
            cells = row.select("td")
            if len(cells) < 2:
                continue
            name = normalise(cells[1].get_text(" ", strip=True)).split(" [", 1)[0]
            result.append(
                entry(
                    name=name,
                    degree_type="MSc",
                    source_url=CATALOG_URL,
                    base_url=CATALOG_URL,
                )
            )
        return result
