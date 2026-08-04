from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://hwxy.nju.edu.cn/English/StudyatNJU/Admissions/"
    "DegreeProgramsTaughtinEnglish/index.html"
)
APPLICATION_URL = (
    "https://hwxy.nju.edu.cn/English/StudyatNJU/Admissions/MastersPrograms/index.html"
)


class NanjingAdapter(BaseProgrammeAdapter):
    university_id = "nanjing-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 8

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index_html = fetcher(CATALOG_URL)
        items = _catalog_items(index_html)
        detail_pages = {str(item["url"]): fetcher(str(item["url"])) for item in items}
        fetcher(APPLICATION_URL)
        return self.parse_catalog(index_html, detail_pages)

    def parse_catalog(
        self,
        index_html: str,
        detail_pages: dict[str, str],
    ) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in _catalog_items(index_html):
            source_url = str(item.get("url", "")).strip()
            title = normalise(item.get("title", ""))
            detail_html = detail_pages.get(source_url, "")
            detail_text = normalise(
                BeautifulSoup(detail_html, "html.parser").get_text(" ", strip=True)
            )
            if (
                not source_url.startswith("https://hwxy.nju.edu.cn/")
                or not title
                or re.search(r"\bmaster(?:['’]s|s)?\b", detail_text, re.I) is None
            ):
                continue
            name = re.sub(r"^\d{6}\s+", "", title).strip()
            programme_id = f"nanjing-english-{slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Nanjing University",
                department="English-taught degree programmes",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Nanjing's official English-taught degree directory and the "
                    "programme page confirm this master's route. The admissions "
                    "page publishes only month-and-day guidance without a complete "
                    "cycle-specific exact opening date, so no dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-english-degree-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Nanjing's official English-taught directory contained "
                f"{len(result)} verified master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _catalog_items(html: str) -> list[dict]:
    match = re.search(r"var\s+dataList\s*=\s*(\[.*?\]);", html, re.S)
    if match is None:
        raise ValueError("Nanjing's official degree directory data is missing")
    payload = json.loads(match.group(1))
    return [
        item
        for page in payload
        if isinstance(page, dict)
        for item in page.get("infolist", [])
        if isinstance(item, dict)
    ]
