from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.ukm.my/studyukm/postgraduate/"
APPLICATION_URL = "https://join.ukm.my/"


class UKMAdapter(OfficialCatalogAdapter):
    university_id = "universiti-kebangsaan-malaysia-ukm"
    school_prefix = "ukm"
    institution_name = "Universiti Kebangsaan Malaysia"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-studyukm-masters-directory"

    def __init__(self, minimum_expected_programmes: int = 50) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index = BeautifulSoup(fetcher(CATALOG_URL), "html.parser")
        detail_urls = sorted(
            {
                urljoin(CATALOG_URL, str(link.get("href", "")))
                for link in index.select('a[href*="/studyukm/master-"]')
                if not urlparse(str(link.get("href", ""))).path.endswith(".pdf")
            }
        )
        if not detail_urls:
            raise ValueError("StudyUKM exposed no master's faculty pages")
        entries: list[CatalogEntry] = []
        for detail_url in detail_urls:
            entries.extend(self.extract_entries(fetcher(detail_url), detail_url))
        return self._catalog(entries)

    def extract_entries(
        self,
        html: str,
        source_url: str = CATALOG_URL,
    ) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        programme_content = None
        for title in soup.select(".elementor-toggle-title"):
            if normalise(title.get_text(" ", strip=True)).casefold() == "programme":
                programme_content = title.find_next(
                    "div", class_="elementor-tab-content"
                )
                break
        if programme_content is None:
            return []

        entries: list[CatalogEntry] = []
        degree_heading = ""
        for paragraph in programme_content.select("p"):
            value = normalise(paragraph.get_text(" ", strip=True)).strip(" -*")
            lower = value.casefold()
            structural_text = any(
                phrase in lower
                for phrase in (
                    "mode of study",
                    "mode a :",
                    "mode b :",
                    "mode c :",
                    "requirements for",
                    "registration status",
                )
            ) or lower.startswith(("full time", "part time"))
            if structural_text:
                degree_heading = ""
                continue
            if not value or lower.startswith(
                ("full time", "part time", "master programmes", "programme")
            ):
                continue
            if paragraph.select_one("strong,b") and lower.startswith("master"):
                degree_heading = value
                continue
            if lower.startswith("master"):
                name = value
                degree_heading = ""
            elif degree_heading:
                name = (
                    degree_heading
                    if degree_heading.casefold().endswith(value.casefold())
                    else f"{degree_heading} in {value}"
                )
            else:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=(degree_heading or value).split(" in ", 1)[0],
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
