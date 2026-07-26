from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "universit-paris-saclay"
CATALOG_URL = "https://www.universite-paris-saclay.fr/en/education/masters-degree"
APPLICATION_URL = "https://www.universite-paris-saclay.fr/en/admission/masters-applications-and-enrolment"


class ParisSaclayAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 65) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        application_text = " ".join(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").stripped_strings
        )
        if (
            "Applications must be submitted on the INCEPTION platform"
            not in application_text
        ):
            raise ValueError("Paris-Saclay official application policy was unavailable")
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = {}
        for card in soup.select("article.licence"):
            link = card.select_one('a[href*="/education/masters-degree/"]')
            title = card.select_one("h3")
            if link is None or title is None:
                continue
            name = " ".join(title.stripped_strings)
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            programme_id = f"paris-saclay-{_slug(name)}-master"
            if name == "Computer Science":
                programme_id = "paris-saclay-computer-science-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=f"{name} Master's degree",
                degree_type="Master",
                faculty="Université Paris-Saclay",
                department=name,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text="Paris-Saclay publishes application routes by year and programme, but this official catalogue does not provide one exact opening and closing pair for the whole master's field. No dates are inferred.",
                parse_status="no-deadline",
                retrieval_method="official-masters-directory",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Paris-Saclay catalogue contained {len(result)} master's fields; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
