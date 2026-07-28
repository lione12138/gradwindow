from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "university-of-california-san-diego-ucsd"
CATALOG_URL = "https://catalog.ucsd.edu/graduate/degrees-offered/index.html"
APPLICATION_URL = "https://grad.ucsd.edu/admissions/programs.html"
EXISTING_COMPUTER_SCIENCE_ID = "ucsd-computer-science-ms"
MASTER_AWARDS = (
    "MCEPA",
    "MENG",
    "MPAC",
    "MDS",
    "MED",
    "MFA",
    "MIA",
    "MBA",
    "MPH",
    "MPP",
    "MAS",
    "MA",
    "MS",
)
MASTER_RE = re.compile(rf"\b({'|'.join(MASTER_AWARDS)})\b", re.I)


class UCSDAdapter(BaseProgrammeAdapter):
    """Discover master's degrees from UC San Diego's official catalogue."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def __init__(self, minimum_expected_programmes: int = 85) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        department = "UC San Diego"
        main = soup.select_one("#main-content") or soup
        for node in main.find_all(["h4", "li"]):
            if node.name == "h4":
                department = _normalise(node.get_text(" ", strip=True))
                continue
            text = (
                _normalise(node.get_text(" ", strip=True))
                .replace("†", "")
                .replace("*", "")
            )
            awards = []
            for match in MASTER_RE.finditer(text):
                award = match.group(1)
                canonical = next(
                    item for item in MASTER_AWARDS if item == award.upper()
                )
                if canonical not in awards:
                    awards.append(canonical)
            if not awards:
                continue
            first_award = min(text.upper().rfind(award) for award in awards)
            base_name = text[:first_award].rstrip(" ,")
            if not base_name:
                continue
            for award in awards:
                name = f"{base_name} {award}"
                programme_id = f"ucsd-{_slug(base_name)}-{award.lower()}"
                if base_name == "Computer Science" and award == "MS":
                    programme_id = EXISTING_COMPUTER_SCIENCE_ID
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=award,
                    faculty="UC San Diego",
                    department=department,
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "UC San Diego's official catalogue confirms this master's "
                        "degree. Deadlines are programme-specific; no exact "
                        "opening-and-closing pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-degree-catalogue",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: (item.name, item.id))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "UC San Diego's official catalogue contained "
                f"{len(result)} master's degrees; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()
