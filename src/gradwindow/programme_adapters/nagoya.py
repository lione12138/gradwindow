from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = "https://admissions.g30.nagoya-u.ac.jp/graduate-2/"
APPLICATION_URL = "https://internationaladmissions-nagoya-u.jp/"


class NagoyaAdapter(BaseProgrammeAdapter):
    university_id = "nagoya-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "October or April, depending on programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 15

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for table in soup.select("table"):
            for row in table.select("tr"):
                cells = row.find_all("td")
                if len(cells) < 4 or cells[2].select_one("img") is None:
                    continue
                source = cells[0].select_one("a[href]")
                if source is None:
                    continue
                name = normalise(cells[0].get_text(" ", strip=True))
                faculty = normalise(cells[1].get_text(" ", strip=True))
                if not name:
                    continue
                programme_id = (
                    f"nagoya-g30-{slug(name)}-{slug(faculty or 'nagoya')}-master"
                )
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type="MPH" if "PUBLIC HEALTH" in name.upper() else "Master",
                    faculty=faculty or "Nagoya University",
                    department=faculty or "Nagoya University",
                    source_url=urljoin(CATALOG_URL, str(source.get("href", ""))),
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Nagoya's official English-taught graduate catalogue confirms "
                        "this master's programme. The official page says programme "
                        "categories use different admissions timelines and does not "
                        "publish a current complete pair of exact dates here, so no "
                        "dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-english-graduate-programme-table",
                    evidence_quality="official-full-text",
                )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Nagoya's official directory contained "
                f"{len(result)} English-taught master's programmes; expected at "
                f"least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
