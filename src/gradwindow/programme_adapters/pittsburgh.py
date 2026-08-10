from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import degree_from, normalise, slug

CATALOG_URL = "https://catalog.upp.pitt.edu/content.php?catoid=242&navoid=27789"
ADMISSIONS_URL = "https://www.gradstudies.pitt.edu/admissions"


class PittsburghAdapter(BaseProgrammeAdapter):
    university_id = "university-of-pittsburgh"
    catalog_url = CATALOG_URL
    admissions_url = ADMISSIONS_URL
    application_url = ADMISSIONS_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-acalog-masters-section"
    catalogue_limitation_reason = (
        "Pitt has no central graduate admissions office. Its official admissions "
        "page says applications and requirements are managed by 14 graduate and "
        "professional schools, so exact windows must be monitored by programme."
    )

    def __init__(self, minimum_expected_programmes: int = 150) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue = self.parse_catalog(fetcher(CATALOG_URL))
        admissions_text = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "applications for admission" not in admissions_text or (
            "14 graduate and professional schools" not in admissions_text
        ):
            raise ValueError("Pitt's distributed graduate admissions policy is missing")
        return catalogue

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        heading = next(
            (
                strong
                for strong in soup.find_all("strong")
                if normalise(strong.get_text(" ", strip=True)).casefold()
                in {"master's", "master’s"}
            ),
            None,
        )
        programme_list = heading.parent.find_next_sibling("ul") if heading else None
        if programme_list is None or "program-list" not in programme_list.get(
            "class", []
        ):
            raise ValueError("Pitt's official Master's catalogue section is missing")

        programmes: dict[str, DiscoveredProgramme] = {}
        for link in programme_list.select('a[href*="preview_program.php"]'):
            name = normalise(link.get_text(" ", strip=True))
            if not name:
                continue
            source_url = urljoin(CATALOG_URL, link["href"])
            programme_id = f"pittsburgh-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_from(name),
                faculty="University of Pittsburgh graduate and professional schools",
                department=(
                    "University of Pittsburgh graduate and professional schools"
                ),
                source_url=source_url,
                application_url=ADMISSIONS_URL,
                windows=[],
                deadline_text=(
                    "Programme found in the official 2026-2027 Master's catalogue "
                    "section. Pitt says its graduate schools manage applications "
                    "separately, so no central exact window is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Pitt catalogue contained {len(result)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
