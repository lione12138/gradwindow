from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.uclouvain.be/fr/catalogue-formations/masters-2026"
APPLICATION_URL = "https://uclouvain.be/en/study/admission.html"
_DEGREE_RE = re.compile(r"^Master\s*\[(?P<credits>\d+)]", re.IGNORECASE)


class UCLouvainAdapter(OfficialCatalogAdapter):
    university_id = "universit-catholique-de-louvain-ucl"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "uclouvain"
    institution_name = "UCLouvain"
    retrieval_method = "official-2026-2027-master-catalogue"
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)

    def __init__(self, minimum_expected_programmes: int = 125) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select("a[href]"):
            name = normalise(link.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            degree_type = _degree_type(name)
            if degree_type is None or not _is_current_programme(source_url):
                continue
            entries.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree_type,
                    source_url=source_url,
                )
            )
        return entries


def _degree_type(name: str) -> str | None:
    match = _DEGREE_RE.match(name)
    if match is not None:
        return f"Master {match.group('credits')}"
    if name.casefold().startswith("master de spécialisation"):
        return "Advanced Master"
    return None


def _is_current_programme(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.hostname.endswith("uclouvain.be")
        and parsed.path.startswith("/prog-2026-")
    )
