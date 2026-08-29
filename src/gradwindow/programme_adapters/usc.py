from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://www.usc.edu/graduate-professional/"
APPLICATION_URL = "https://gradadm.usc.edu/apply/"


class USCAdapter(OfficialCatalogAdapter):
    university_id = "university-of-southern-california"
    school_prefix = "usc"
    institution_name = "University of Southern California"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-unfiltered-graduate-programme-directory"

    def __init__(self, minimum_expected_programmes: int = 300) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        next_url: str | None = CATALOG_URL
        visited: set[str] = set()
        entries: list[CatalogEntry] = []
        while next_url:
            if next_url in visited or len(visited) >= 80:
                raise ValueError("USC programme pagination did not terminate")
            visited.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            next_url = _next_catalogue_page(html)
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select("li a[href]"):
            if link.get_text(" ", strip=True).casefold() != "learn more":
                continue
            item = link.find_parent("li")
            heading = item.select_one(".item-title") if item is not None else None
            name = heading.get_text(" ", strip=True) if heading is not None else ""
            source_url = str(link.get("href", ""))
            if (
                not name
                or "catalogue.usc.edu/" not in source_url
                or not _is_master_programme(name)
            ):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


_MASTER_DEGREE_CODES = {
    "IPPM",
    "LLM",
    "MA",
    "MAARS",
    "MAAS",
    "MACC",
    "MACM",
    "MARCH",
    "MAT",
    "MBA",
    "MBS",
    "MBT",
    "MBV",
    "MCG",
    "MCL",
    "MCM",
    "MDR",
    "MED",
    "MFA",
    "MHA",
    "MHC",
    "MITLE",
    "MLARCH",
    "MMLIS",
    "MM",
    "MMS",
    "MNLM",
    "MPA",
    "MPAP",
    "MPD",
    "MPDS",
    "MPH",
    "MPP",
    "MRED",
    "MS",
    "MSAB",
    "MSL",
    "MSM",
    "MSN-FNP",
    "MSW",
    "MUP",
    "MVA",
}
_DEGREE_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9-])([A-Za-z][A-Za-z0-9-]{1,12})(?![A-Za-z0-9-])"
)


def _is_master_programme(name: str) -> bool:
    if re.search(r"\bmaster\s+(?:of|in)\b", name, re.IGNORECASE):
        return True
    return any(
        match.group(1).upper() in _MASTER_DEGREE_CODES
        for match in _DEGREE_CODE_RE.finditer(name)
    )


def _next_catalogue_page(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    next_link = next(
        (
            link
            for link in soup.select("nav.pager a[href]")
            if link.get_text(" ", strip=True).casefold() == "next page"
        ),
        None,
    )
    if next_link is None:
        return None
    target = urlsplit(urljoin(CATALOG_URL, str(next_link.get("href", ""))))
    if target.hostname != "www.usc.edu" or not re.fullmatch(
        r"/graduate-professional/page/\d+/", target.path
    ):
        raise ValueError("USC catalogue exposed an unexpected pagination URL")
    return urlunsplit((target.scheme, target.netloc, target.path, "", ""))
