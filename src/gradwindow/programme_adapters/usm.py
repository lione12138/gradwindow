from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://admission.usm.my/postgraduate/programmes"
APPLICATION_URL = "https://admission.usm.my/index.php/postgraduate/application"
MASTER_RE = re.compile(
    r"\b(?:Master(?:'s)?|MSc|M\.Sc\.?|MA|MBA|MPH|LLM|MEd|MEng|MRes)\b",
    re.IGNORECASE,
)


class USMAdapter(OfficialCatalogAdapter):
    university_id = "universiti-sains-malaysia-usm"
    school_prefix = "usm"
    institution_name = "Universiti Sains Malaysia"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 240
    retrieval_method = "official-postgraduate-programme-directory"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for anchor in soup.select("a[href]"):
            name = anchor.get_text(" ", strip=True)
            href = str(anchor["href"])
            if not MASTER_RE.search(name) or "/index.php/" not in href:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=href,
                    base_url=CATALOG_URL,
                )
            )
        return entries
