from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://studyathit.hit.edu.cn/18359/list.htm"
APPLICATION_URL = "https://hit.at0086.cn/student"
_CATALOGUE_LABELS = {
    "Master's Degree Programs (Chinese-taught)-Major List.xlsx": "Chinese",
    "Master's Degree Programs (English-taught)-Major List.xlsx": "English",
}


class HITAdapter:
    university_id = "harbin-institute-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-international-master-xlsx-catalogues"

    def __init__(self, minimum_expected_programmes: int = 50) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        sources = _catalogue_sources(fetcher(CATALOG_URL))
        programmes = {
            programme.id: programme
            for source_url, language in sources
            for programme in _xlsx_programmes(
                fetcher(source_url), source_url=source_url, language=language
            )
        }
        rows = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(rows) < self.minimum_expected_programmes:
            raise ValueError(
                f"HIT catalogues contained {len(rows)} master's routes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=rows)


def _catalogue_sources(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    sources = {}
    for link in soup.select("a[href]"):
        label = normalise(link.get_text(" ", strip=True))
        language = _CATALOGUE_LABELS.get(label)
        if language is None:
            continue
        source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
        if _is_official_xlsx(source_url):
            sources[language] = source_url
    if set(sources) != {"Chinese", "English"}:
        raise ValueError("HIT master page did not expose both official XLSX catalogues")
    return sorted((url, language) for language, url in sources.items())


def _xlsx_programmes(
    value: str,
    *,
    source_url: str,
    language: str,
) -> list[DiscoveredProgramme]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("HIT catalogue did not return XLSX rows") from exc
    worksheets = payload.get("worksheets") if isinstance(payload, dict) else None
    if not isinstance(worksheets, list) or not worksheets:
        raise ValueError("HIT XLSX payload did not contain worksheets")
    rows = worksheets[0].get("rows")
    if not isinstance(rows, list) or len(rows) < 3:
        raise ValueError("HIT XLSX catalogue was empty")

    faculty = ""
    programmes = []
    language_label = f"{language}-taught"
    for row in rows[2:]:
        if not isinstance(row, list) or len(row) < 4:
            continue
        faculty = _english_label(row[1]) or faculty
        name = _english_label(row[2])
        taught_in = _english_label(row[3])
        if not faculty or not name or language.casefold() not in taught_in.casefold():
            continue
        programmes.append(
            DiscoveredProgramme(
                id=(f"hit-{slug(faculty)}-{slug(name)}-{language.casefold()}"),
                name=f"{name} ({language_label})",
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    f"Programme is listed in HIT's official {language_label} "
                    "international master's XLSX. HIT describes applications as "
                    "rolling but does not publish an exact opening-date pair."
                ),
                parse_status="no-deadline",
                retrieval_method="official-international-master-xlsx-catalogues",
                evidence_quality="official-full-text",
            )
        )
    return programmes


def _english_label(value: object) -> str:
    lines = [normalise(line) for line in str(value or "").splitlines()]
    return next((line for line in reversed(lines) if line), "")


def _is_official_xlsx(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.hostname.endswith(".hit.edu.cn")
        and parsed.path.casefold().endswith(".xlsx")
    )
