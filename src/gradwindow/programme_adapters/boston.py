from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.bu.edu/academics/degree-programs/"
APPLICATION_URL = "https://www.bu.edu/admissions/graduate/"
MASTER_AWARDS = {
    "LLM",
    "MA",
    "MAT",
    "MBA",
    "MEng",
    "MFA",
    "MFA/MA",
    "MFA/MS",
    "MM",
    "MPH",
    "MS",
    "MSW",
}


class BostonAdapter(OfficialCatalogAdapter):
    university_id = "boston-university"
    school_prefix = "boston"
    institution_name = "Boston University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 180

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for row in soup.select("li.ma"):
            row_name = next(
                (
                    str(value).strip().rstrip(" (")
                    for value in row.find_all(string=True, recursive=False)
                    if str(value).strip().rstrip(" (")
                ),
                "",
            )
            for link in row.find_all("a", href=True):
                award = link.get_text(" ", strip=True)
                if award not in MASTER_AWARDS:
                    continue
                entries.append(
                    entry(
                        name=f"{row_name} ({award})",
                        degree_type=award,
                        source_url=link["href"],
                        base_url=CATALOG_URL,
                    )
                )
        return entries
