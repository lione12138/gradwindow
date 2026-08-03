from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.lse.ac.uk/study-at-lse/Graduate/Available-programmes"
APPLICATION_URL = (
    "https://www.lse.ac.uk/study-at-lse/Graduate/Prospective-students/How-to-Apply"
)
PROGRAMME_PATH_RE = re.compile(r"/study-at-lse/graduate/", re.I)
MASTER_RE = re.compile(r"\b(MSc|MA|LLM|MPA|MPH|MRes|Master)\b", re.I)
CODE_RE = re.compile(r"^(?:\*NEW\*\s*)?[A-Z0-9]{4}\s+")


class LSEAdapter(OfficialCatalogAdapter):
    university_id = "london-school-of-economics-and-political-science-lse"
    school_prefix = "lse"
    institution_name = "London School of Economics and Political Science"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 130

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.find_all("a", href=PROGRAMME_PATH_RE):
            raw_name = " ".join(link.get_text(" ", strip=True).split())
            if not MASTER_RE.search(raw_name) or re.search(
                r"MPhil|PhD", raw_name, re.I
            ):
                continue
            name = CODE_RE.sub("", raw_name).strip()
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
