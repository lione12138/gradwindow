from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)

UNIVERSITY_ID = "kaist"
CATALOG_URL = "https://admission.kaist.ac.kr/intl-graduate/Discover/ExplorePrograms"
TIMELINE_URL = "https://admission.kaist.ac.kr/intl-graduate/Admission/YearlyTimelines"
APPLICATION_URL = "https://admission.kaist.ac.kr/intl-graduate/Admission/Apply"


class KAISTAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Spring 2027"
    application_opens_at_basis = "official"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 34) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        timeline = " ".join(
            BeautifulSoup(fetcher(TIMELINE_URL), "html.parser").stripped_strings
        )
        match = re.search(
            r"Spring 2027\s*Entry:\s*([A-Z][a-z]+ \d{1,2})\s*[–-]\s*([A-Z][a-z]+ \d{1,2}, 2026)",
            timeline,
        )
        if not match:
            raise ValueError("KAIST Spring 2027 timeline lacks exact dates")
        opens_at = (
            datetime.strptime(f"{match.group(1)}, 2026", "%B %d, %Y").date().isoformat()
        )
        closes_at = datetime.strptime(match.group(2), "%B %d, %Y").date().isoformat()
        return self._parse(fetcher(CATALOG_URL), opens_at, closes_at)

    def _parse(self, html: str, opens_at: str, closes_at: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = []
        for title in soup.select("h5.h-accordion-tit"):
            container = title.find_parent("li")
            if container is None or "Master's" not in container.get_text(
                " ", strip=True
            ):
                continue
            name_node = title.find("span")
            name = " ".join((name_node or title).stripped_strings)
            heading = title.find_previous("h4")
            faculty = " ".join(heading.stripped_strings) if heading else "KAIST"
            source_link = title.select_one("a[href]")
            source_url = (
                str(source_link.get("href"))
                if source_link and "kaist.ac.kr" in str(source_link.get("href"))
                else CATALOG_URL
            )
            programmes.append(
                DiscoveredProgramme(
                    id=f"kaist-{_slug(name)}-master",
                    name=f"{name} Master's",
                    degree_type="Master",
                    faculty=faculty,
                    department=name,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[
                        DiscoveredWindow(
                            round="Spring admission",
                            opens_at=opens_at,
                            closes_at=closes_at,
                            intake=self.intake,
                            applicant_categories=["international-students"],
                            source_url=TIMELINE_URL,
                        )
                    ],
                    deadline_text="KAIST's official international graduate timeline publishes the exact Spring 2027 application period.",
                    parse_status="parsed",
                    retrieval_method="official-programme-directory",
                    evidence_quality="official-full-text",
                )
            )
        programmes.sort(key=lambda item: item.name)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"KAIST catalogue contained {len(programmes)} master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
