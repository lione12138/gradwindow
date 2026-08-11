from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://lxs.szu.edu.cn/info/1278/5777.htm"
APPLICATION_URL = "https://en.szu.edu.cn/info/1024/1905.htm"
NON_PROGRAMME_LABELS = {
    "Arts",
    "Liberal Arts",
    "Science & Engineering",
    "Yuehai",
    "Lihu",
}


class ShenzhenAdapter(OfficialCatalogAdapter):
    university_id = "shenzhen-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "shenzhen"
    institution_name = "Shenzhen University"
    minimum_expected_programmes = 23
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-masters-table"
    catalogue_limitation_reason = (
        "Shenzhen University's official 2026 international admissions table "
        "enumerates the master's programmes currently offered to international "
        "applicants. The central page does not publish a next-cycle exact opening "
        "and closing pair."
    )

    def __init__(self, minimum_expected_programmes: int = 23) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        for table_row in soup.select("table tr"):
            name = next(
                (
                    candidate
                    for cell in table_row.select("th,td")
                    if (candidate := _english_label(cell.get_text(" ", strip=True)))
                    and _is_programme(candidate)
                ),
                None,
            )
            if name is None:
                continue
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master",
                    source_url=CATALOG_URL,
                )
            )
        return rows


def _english_label(value: str) -> str:
    ascii_value = "".join(
        character if ord(character) < 128 else " " for character in value
    )
    return normalise(ascii_value).strip(" *")


def _is_programme(value: str) -> bool:
    lower = value.casefold()
    if value in NON_PROGRAMME_LABELS or "@" in value or value.isdigit():
        return False
    return not any(
        marker in lower
        for marker in (
            "college of ",
            " school",
            "school of ",
            "division of ",
        )
    )
