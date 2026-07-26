from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "university-of-texas-at-austin"
CATALOG_URL = "https://gradschool.utexas.edu/degrees-programs"
APPLICATION_URL = "https://gradschool.utexas.edu/admissions/apply"
MASTER_CODE_RE = re.compile(r"^(?:M|LLM|MBA|MPA|MPH|MFA|MArch|MSW)[A-Za-z.]*$")


class UTAustinAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 115) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = {}
        for table in soup.select("table"):
            heading = table.find_previous(["h2", "h3"])
            faculty = heading.get_text(" ", strip=True) if heading else "UT Austin"
            for row in table.select("tr"):
                cells = row.find_all(["td", "th"], recursive=False)
                if len(cells) < 6 or cells[0].name == "th":
                    continue
                name = re.sub(r"\s+\(\d+\)$", "", cells[0].get_text(" ", strip=True))
                link = cells[0].select_one("a[href]")
                source_url = (
                    urljoin(CATALOG_URL, str(link.get("href", "")))
                    if link
                    else CATALOG_URL
                )
                degrees = [
                    value.strip()
                    for value in re.split(r"[,;/]", cells[4].get_text(" ", strip=True))
                ]
                for degree in degrees:
                    compact = degree.replace(" ", "")
                    if "Ph.D" in compact or not MASTER_CODE_RE.match(compact):
                        continue
                    normalised_degree = compact.replace(".", "")
                    programme_id = f"ut-austin-{_slug(name)}-{_slug(normalised_degree)}"
                    if name == "Computer Science" and normalised_degree in {
                        "MS",
                        "MSCS",
                    }:
                        programme_id = "ut-austin-computer-science-ms"
                        normalised_degree = "MS"
                    programmes[programme_id] = DiscoveredProgramme(
                        id=programme_id,
                        name=f"{normalised_degree} in {name}",
                        degree_type=normalised_degree,
                        faculty=faculty,
                        department=name,
                        source_url=source_url,
                        application_url=APPLICATION_URL,
                        windows=[],
                        deadline_text="UT Austin's official degree table publishes programme closing deadlines but not an exact common opening date. No opening date is inferred.",
                        parse_status="no-deadline",
                        retrieval_method="official-degree-table",
                        evidence_quality="official-full-text",
                    )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UT Austin catalogue contained {len(result)} master's degrees; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
