from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://isa.ustc.edu.cn/xs/info/master_ch.asp"
APPLICATION_URL = "https://ic.ustc.edu.cn/en/v7info.php?Nav_x=9"


class USTCAdapter(OfficialCatalogAdapter):
    university_id = "university-of-science-and-technology-of-china"
    school_prefix = "ustc"
    institution_name = "University of Science and Technology of China"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 65
    retrieval_method = "official-master-discipline-directory"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        table = next(
            (
                candidate
                for candidate in soup.select("table")
                if "First-level discipline" in candidate.get_text(" ", strip=True)
            ),
            None,
        )
        if table is None:
            raise ValueError("USTC master directory table was not found")
        entries: list[CatalogEntry] = []
        first_level = ""
        for row in table.select("tr"):
            cells = row.select("td")
            if len(cells) >= 2:
                first_level = normalise(cells[0].get_text(" ", strip=True))
                second_level = normalise(cells[-1].get_text(" ", strip=True))
            elif len(cells) == 1 and first_level:
                second_level = normalise(cells[0].get_text(" ", strip=True))
            else:
                continue
            if not first_level or not second_level:
                continue
            name = (
                second_level
                if first_level.casefold() == second_level.casefold()
                else f"{first_level}: {second_level}"
            )
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=CATALOG_URL,
                    base_url=CATALOG_URL,
                )
            )
        return entries
