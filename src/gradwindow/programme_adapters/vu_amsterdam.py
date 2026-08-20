from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import (
    DiscoveredCatalog,
    DiscoveredWindow,
    Fetcher,
    OfficialSourceTransportError,
    ParserZeroResultError,
)
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://vu.nl/en/education/master/programmes"
SEARCH_API_URL = "https://vu.nl/api/search"
APPLICATION_URL = "https://vu.nl/en/education/more-about/apply-masters-programme"
PROGRAMME_PATH_RE = re.compile(r"^/en/education/master/[^/]+/?$", re.I)
DATE_RE = r"\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}"


class VUAmsterdamAdapter(OfficialCatalogAdapter):
    university_id = "vrije-universiteit-amsterdam"
    school_prefix = "vu-amsterdam"
    institution_name = "Vrije Universiteit Amsterdam"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 100
    retrieval_method = "official-study-search-api"

    def __init__(
        self,
        minimum_expected_programmes: int = 100,
        *,
        search_api_fetcher: Callable[[], str] | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.search_api_fetcher = search_api_fetcher or self._fetch_search_api

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        api_error: Exception | None = None
        try:
            catalog = self.parse_catalog(self.search_api_fetcher())
        except Exception as exc:
            api_error = exc
            catalog = self._parse_static_catalog(fetcher(CATALOG_URL))
            catalog.warnings.append(
                {
                    "reason": "TRANSPORT_ERROR",
                    "message": (
                        "VU Amsterdam's official study-search API failed; the "
                        "official static programme catalogue fallback was used."
                    ),
                    "sourceUrl": SEARCH_API_URL,
                    "fallback": "official-static-catalogue",
                    "errorType": type(api_error).__name__,
                }
            )

        try:
            application_html = fetcher(APPLICATION_URL)
        except Exception as exc:
            raise OfficialSourceTransportError(
                "VU Amsterdam's critical application-deadline page was unavailable"
            ) from exc
        windows_by_programme = _february_windows(application_html)
        date_signal = re.search(
            r"application deadlines for international students wishing to start "
            r"in February\s+20\d{2}",
            normalise(
                BeautifulSoup(application_html, "html.parser").get_text(" ", strip=True)
            ),
            re.I,
        )
        if date_signal and not windows_by_programme:
            raise ParserZeroResultError(
                "VU Amsterdam's February deadline section contained date signals "
                "but produced zero programme windows."
            )
        for programme in catalog.programmes:
            windows = windows_by_programme.get(programme.name.casefold(), [])
            if not windows:
                continue
            programme.windows = windows
            programme.deadline_text = (
                "VU Amsterdam's official application page publishes the February "
                "intake deadline by programme and EU/non-EU category. It does not "
                "publish an exact opening day for this intake."
            )
            programme.parse_status = "incomplete"
        return catalog

    def _fetch_search_api(self) -> str:
        body = {
            "queryType": "full",
            "filter": (
                "ContentType eq 'programme_page' and "
                "ItemType/any(c: search.in(c, 'Study')) and "
                "ItemType/any(c: search.in(c, 'Master')) and Language eq 'en'"
            ),
            "search": "*",
            "count": True,
            "skip": 0,
            "top": 1000,
            "orderby": "Title asc",
        }
        last_error: Exception | None = None
        for _attempt in range(3):
            try:
                response = httpx.post(
                    SEARCH_API_URL,
                    json=body,
                    headers={
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "index": "vunl",
                        "api-version": "2020-06-30",
                        "Referer": CATALOG_URL,
                    },
                    timeout=90,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                last_error = exc
        raise OfficialSourceTransportError(
            "VU Amsterdam study-search API failed after three attempts"
        ) from last_error

    def _parse_static_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        entries = [
            CatalogEntry(
                name=normalise(link.get_text(" ", strip=True)),
                degree_type="Master",
                source_url=urljoin(CATALOG_URL, str(link.get("href", ""))),
            )
            for link in soup.select("a[href]")
            if PROGRAMME_PATH_RE.match(
                urlsplit(urljoin(CATALOG_URL, str(link.get("href", "")))).path
            )
            and normalise(link.get_text(" ", strip=True))
        ]
        self.retrieval_method = "official-static-programme-catalogue"
        return self._catalog(entries)

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = json.loads(payload)["value"]
        entries = []
        for row in rows:
            item_types = set(row.get("ItemType") or [])
            content_type = str(row.get("ContentType") or "")
            source_url = str(row.get("Url") or "")
            if (
                not {"Study", "Master"}.issubset(item_types)
                or "PreMaster" in item_types
                or "Specialization" in item_types
                or (content_type and content_type != "programme_page")
                or not PROGRAMME_PATH_RE.match(urlsplit(source_url).path)
            ):
                continue
            entries.append(
                entry(
                    name=str(row.get("Title") or ""),
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _february_windows(html: str) -> dict[str, list[DiscoveredWindow]]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    intake_match = re.search(r"start in February\s+(20\d{2})", text, re.I)
    non_eu_match = re.search(rf"(?P<date>{DATE_RE})\s+for non-EU citizens", text, re.I)
    mathematics_match = re.search(
        rf"(?P<date>{DATE_RE})\s+for EU citizens for the Master programmes? "
        r"in Mathematics",
        text,
        re.I,
    )
    law_match = re.search(
        rf"(?P<date>{DATE_RE})\s+for EU citizens for the Master in Law",
        text,
        re.I,
    )
    if not all((intake_match, non_eu_match, mathematics_match, law_match)):
        return {}
    intake = f"February {intake_match.group(1)}"
    non_eu_deadline = _iso_date(non_eu_match.group("date"))
    definitions = {
        "mathematics": (
            ("eu-efta", _iso_date(mathematics_match.group("date"))),
            ("non-eu-efta", non_eu_deadline),
        ),
        "law": (
            ("eu-efta", _iso_date(law_match.group("date"))),
            ("non-eu-efta", non_eu_deadline),
        ),
    }
    return {
        programme: [
            DiscoveredWindow(
                round="February intake application deadline",
                applicant_categories=[category],
                opens_at=None,
                closes_at=closes_at,
                intake=intake,
                source_url=APPLICATION_URL,
            )
            for category, closes_at in rows
        ]
        for programme, rows in definitions.items()
    }


def _iso_date(value: str) -> str:
    return datetime.strptime(value, "%d %B %Y").date().isoformat()
