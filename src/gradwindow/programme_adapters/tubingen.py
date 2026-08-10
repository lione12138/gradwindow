from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = (
    "https://uni-tuebingen.de/en/study/finding-a-course/degree-programs-available/"
)
ADMISSIONS_URL = (
    "https://uni-tuebingen.de/en/study/application-and-enrollment/masters-degree.html"
)


class TubingenAdapter(OfficialCatalogAdapter):
    university_id = "university-of-tubingen"
    catalog_url = CATALOG_URL
    application_url = ADMISSIONS_URL
    school_prefix = "tubingen"
    institution_name = "University of Tübingen"
    minimum_expected_programmes = 80
    window_watch_urls = (CATALOG_URL, ADMISSIONS_URL)
    retrieval_method = "official-paginated-degree-programme-catalogue"
    catalogue_limitation_reason = (
        "Tübingen publishes programme-specific application dates. The central "
        "master's admissions page links separate semester lists, so catalogue "
        "discovery is complete while exact-window discovery remains monitored."
    )

    def __init__(self, minimum_expected_programmes: int = 80) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries: list[CatalogEntry] = []
        next_url: str | None = CATALOG_URL
        seen = set()
        while next_url and next_url not in seen:
            seen.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            next_url = _next_page_url(html)
        policy = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "different application deadlines" not in policy:
            raise ValueError("Tübingen's programme-specific deadline policy is missing")
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for box in soup.select(".ut-box"):
            link = box.select_one('a[href*="degree-programs-available/detail/course/"]')
            degree = _label_value(box, "Degree")
            if link is None or not degree.casefold().startswith("master"):
                continue
            name = normalise(str(link.get("title", "")))
            if not name:
                heading = box.find(["h2", "h3", "h4"])
                name = normalise(heading.get_text(" ", strip=True) if heading else "")
            rows.append(
                entry(
                    name=name,
                    degree_type=degree,
                    source_url=str(link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return rows


def _label_value(box, label: str) -> str:
    for strong in box.select("strong"):
        if normalise(strong.get_text(" ", strip=True)).casefold() != label.casefold():
            continue
        parent = strong.parent
        text = normalise(parent.get_text(" ", strip=True)) if parent else ""
        return text[len(label) :].strip(" :")
    return ""


def _next_page_url(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        if normalise(link.get_text(" ", strip=True)).casefold() == "next":
            return urljoin(CATALOG_URL, str(link["href"]))
    return None
