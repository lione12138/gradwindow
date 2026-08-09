from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://penerimaan.ui.ac.id/period/requirement/3581"
APPLICATION_URL = "https://enrollment.ui.ac.id/"


class UniversitasIndonesiaAdapter:
    university_id = "universitas-indonesia"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Next published SIMAK S2 intake"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, "https://simak.ui.ac.id/simak-ui/")
    retrieval_method = "official-simak-s2-requirements-archive"

    def __init__(self, minimum_expected_programmes: int = 65) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher) -> DiscoveredCatalog:
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        programmes = _programmes(html)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"UI S2 requirements archive contained {len(programmes)} programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    if "S2 Jalur SIMAK" not in normalise(soup.get_text(" ", strip=True)):
        raise ValueError("UI requirements page was not an official S2 admissions page")
    programmes = {}
    faculty = ""
    for row in soup.select("table tr"):
        cells = row.select("th,td")
        if len(cells) == 1:
            faculty = normalise(cells[0].get_text(" ", strip=True))
            continue
        if len(cells) < 2 or not faculty:
            continue
        name = normalise(cells[0].get_text(" ", strip=True))
        if not name or name == "Program Studi":
            continue
        programme_id = f"ui-{slug(faculty)}-{slug(name)}"
        if faculty == "Ilmu Komputer" and name == "Ilmu Komputer":
            programme_id = "ui-magister-ilmu-komputer"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Magister",
            faculty=faculty,
            department=faculty,
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in UI's stable official SIMAK S2 requirements "
                "archive. Registration moved to the new enrollment service, so the "
                "adapter monitors for the next intake and does not infer exact dates."
            ),
            parse_status="no-deadline",
            retrieval_method="official-simak-s2-requirements-archive",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())
