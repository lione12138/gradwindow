from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://acad.iitb.ac.in/admissions/masters/divisions"
APPLICATION_URL = "https://acad.iitb.ac.in/admissions/masters"
DEGREE_TYPES = (
    "M.Tech",
    "M.Des",
    "MBA",
    "EMBA",
    "MA+PhD",
    "MA.Res",
    "MPP",
    "MSc",
    "MSc+PhD",
    "MDP",
)
CODE_RE = re.compile(r"^\([A-Z0-9]+\)\s*")


class IITBombayAdapter(OfficialCatalogAdapter):
    university_id = "indian-institute-of-technology-bombay-iitb"
    school_prefix = "iitb"
    institution_name = "Indian Institute of Technology Bombay"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 40
    retrieval_method = "official-master-academic-divisions"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for table_index, table in enumerate(soup.select("table")):
            if table_index >= len(DEGREE_TYPES):
                break
            degree_type = DEGREE_TYPES[table_index]
            for row in table.select("tr"):
                cells = row.select("td")
                if len(cells) < 2:
                    continue
                department_link = cells[1].select_one("a[href]")
                source_url = (
                    str(department_link["href"]) if department_link else CATALOG_URL
                )
                names = [
                    normalise(node.get_text(" ", strip=True))
                    for node in cells[0].select(":scope > p")
                ]
                if not names:
                    names = [normalise(cells[0].get_text(" ", strip=True))]
                for value in names:
                    name = CODE_RE.sub("", value).strip()
                    if not name or name.casefold() == "degree/specialization":
                        continue
                    if (
                        degree_type == "EMBA"
                        and name == "Master of Business Administration"
                    ):
                        name = "Executive Master of Business Administration"
                    entries.append(
                        entry(
                            name=name,
                            degree_type=degree_type,
                            source_url=source_url,
                            base_url=CATALOG_URL,
                        )
                    )
        return entries
