from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable

import httpx

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "ku-leuven"
CATALOG_URL = "https://onderwijsaanbod.kuleuven.be/opleidingen/e"
API_URL = "https://onderwijsaanbod.kuleuven.be/api/pg2026/_search"
APPLICATION_URL = (
    "https://www.kuleuven.be/english/study/apply/application-instructions/"
    "apply-to-kuleuven"
)
APPLICATION_WINDOWS_URL = (
    "https://icts.kuleuven.be/apps/tuitionfees/application-windows"
)
INSTITUTION_ID = "50000050"
EXISTING_STATISTICS_ID = "ku-leuven-statistics-data-science-master"


class KULeuvenAdapter(BaseProgrammeAdapter):
    """Discover KU Leuven master's qualifications from its programme-guide API."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL, APPLICATION_WINDOWS_URL)

    def __init__(
        self,
        minimum_expected_programmes: int = 300,
        api_fetcher: Callable[[], str] | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.api_fetcher = api_fetcher or _fetch_api

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_json(self.api_fetcher())

    def parse_json(self, payload: str) -> DiscoveredCatalog:
        data = json.loads(payload)
        records: list[tuple[dict, str, str, str]] = []
        for hit in data.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            if str(source.get("institution")) != INSTITUTION_ID:
                continue
            degree_type = str(source.get("enQualificationDegreeLevel", ""))
            if degree_type not in {"Master's", "Advanced Master's"}:
                continue
            name = _english_title(source.get("qualificationLanguageSet", []))
            qualification_id = str(
                source.get("qualificationId") or source.get("id") or ""
            ).strip()
            if name and qualification_id:
                records.append((source, name, qualification_id, degree_type))
        title_counts = Counter(name for _, name, _, _ in records)
        programmes: dict[str, DiscoveredProgramme] = {}
        for source, base_name, qualification_id, degree_type in records:
            name = base_name
            if title_counts[base_name] > 1:
                language = _original_language(
                    source.get("qualificationLanguageSet", [])
                )
                if language:
                    name = f"{base_name} ({language}-taught)"
            programme_id = f"ku-leuven-{_slug(base_name)}-{qualification_id}-master"
            if _normalise_title(base_name) == "master of statistics and data science":
                programme_id = EXISTING_STATISTICS_ID
            source_url = (
                "https://onderwijsaanbod.kuleuven.be/opleidingen/e/"
                f"CQ_{qualification_id}"
            )
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty="KU Leuven",
                department="KU Leuven",
                source_url=source_url,
                application_url=str(source.get("applyUrl") or APPLICATION_URL),
                windows=[],
                deadline_text=(
                    "KU Leuven publishes programme-specific application windows. "
                    "No exact opening-and-closing pair is assigned until the official "
                    "window tool is deterministically mapped to this qualification."
                ),
                parse_status="no-deadline",
                retrieval_method="official-programme-guide-api",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "KU Leuven's official programme guide contained "
                f"{len(result)} master's qualifications; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _fetch_api() -> str:
    payload = {
        "size": 500,
        "from": 0,
        "_source": [
            "id",
            "institution",
            "qualificationId",
            "enQualificationDegreeLevel",
            "applyUrl",
            "qualificationLanguageSet.qualificationTitleSet.description",
            "qualificationLanguageSet.qualificationTitleSet.qualificationLangu",
            "qualificationLanguageSet.qualificationOriginalLanguSet.qualificationOriginalLangu",
        ],
        "query": {
            "bool": {
                "filter": [
                    {
                        "terms": {
                            "enQualificationDegreeLevel.keyword": [
                                "Master's",
                                "Advanced Master's",
                            ]
                        }
                    },
                    {"term": {"institution": INSTITUTION_ID}},
                ]
            }
        },
    }
    response = httpx.post(
        API_URL,
        json=payload,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
        timeout=90,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def _english_title(language_sets: object) -> str:
    if not isinstance(language_sets, list):
        return ""
    fallback = ""
    for language in language_sets:
        if not isinstance(language, dict):
            continue
        for title in language.get("qualificationTitleSet", []):
            if not isinstance(title, dict):
                continue
            value = re.sub(r"\s+", " ", str(title.get("description", ""))).strip()
            fallback = fallback or value
            if str(title.get("qualificationLangu", "")).upper() == "EN":
                return value
    return fallback


def _original_language(language_sets: object) -> str:
    if not isinstance(language_sets, list):
        return ""
    for language in language_sets:
        if not isinstance(language, dict):
            continue
        for value in language.get("qualificationOriginalLanguSet", []):
            if not isinstance(value, dict):
                continue
            code = str(value.get("qualificationOriginalLangu", "")).upper()
            if code == "EN":
                return "English"
            if code == "NL":
                return "Dutch"
    return ""


def _normalise_title(value: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", value).strip().lower()


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
