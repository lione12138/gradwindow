from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://u-paris.fr/en/programs-taught-in-english/"
MON_MASTER_URL = "https://u-paris.fr/mon-master-trouver-nos-formations/"
ADMISSIONS_URL = (
    "https://u-paris.fr/language/en/admission-as-an-independent-international-student/"
)
MON_MASTER_APPLICATION_URL = "https://www.monmaster.gouv.fr/"
_FRENCH_MONTHS = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}
_WINDOW_RE = re.compile(
    r"calendrier\s+(?P<year>20\d{2}).{0,900}?entre le\s+"
    r"(?P<open_day>\d{1,2})\s+(?P<open_month>[a-zéûôîàèùç]+)\s+et le\s+"
    r"(?P<close_day>\d{1,2})\s+(?P<close_month>[a-zéûôîàèùç]+)\s+"
    r"soumettez vos candidatures",
    re.IGNORECASE,
)


class ParisCiteAdapter(BaseProgrammeAdapter):
    university_id = "universite-paris-cite"
    catalog_url = CATALOG_URL
    admissions_url = MON_MASTER_URL
    application_url = ADMISSIONS_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, MON_MASTER_URL, ADMISSIONS_URL)
    retrieval_method = "official-english-catalogue-and-mon-master-calendar"
    catalogue_status = "partial"
    catalogue_limitation_reason = (
        "The machine-readable official page covers programmes taught in English, "
        "not the university's complete French-language master's catalogue. Mon "
        "Master covers only the relevant first-year national application route."
    )

    def __init__(self, minimum_expected_programmes: int = 35) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = self._programmes(fetcher(CATALOG_URL))
        opens_at, closes_at, intake = self._window(fetcher(MON_MASTER_URL))
        programmes.append(
            DiscoveredProgramme(
                id="paris-cite-mon-master-admissions",
                name="First-year national master's applications (Mon Master)",
                degree_type="Master",
                faculty="Université Paris Cité",
                department="Mon Master admissions route",
                source_url=MON_MASTER_URL,
                application_url=MON_MASTER_APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="Main Mon Master application phase",
                        applicant_categories=["all"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=intake,
                        source_url=MON_MASTER_URL,
                    )
                ],
                deadline_text=(
                    "Université Paris Cité's official Mon Master guide publishes "
                    "this exact application phase for the applicable first-year "
                    "national master's route."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)

    def _programmes(self, html: str) -> list[DiscoveredProgramme]:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select("article a[href]"):
            name = normalise(link.get_text(" ", strip=True))
            if not re.search(r"\bmaster\b", name, re.IGNORECASE):
                continue
            programme_id = f"paris-cite-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Université Paris Cité",
                department="English-taught programmes",
                source_url=link["href"],
                application_url=ADMISSIONS_URL,
                windows=[],
                deadline_text=(
                    "Programme found on Université Paris Cité's official list of "
                    "programmes taught in English. Application routes vary, so no "
                    "programme-specific exact dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Paris Cité English catalogue contained {len(result)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        return result

    @staticmethod
    def _window(html: str) -> tuple[str, str, str]:
        text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        match = _WINDOW_RE.search(text)
        if match is None:
            raise ValueError("Paris Cité's exact Mon Master calendar is missing")
        year = int(match.group("year"))
        try:
            open_month = _FRENCH_MONTHS[match.group("open_month").casefold()]
            close_month = _FRENCH_MONTHS[match.group("close_month").casefold()]
        except KeyError as exc:
            raise ValueError("Paris Cité's Mon Master month is unrecognised") from exc
        opens_at = date(year, open_month, int(match.group("open_day")))
        closes_at = date(year, close_month, int(match.group("close_day")))
        return opens_at.isoformat(), closes_at.isoformat(), f"Autumn {year}"
