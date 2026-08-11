from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://www.uni-wuerzburg.de/en/studying-at-jmu/studienangelegenheiten/"
    "application-and-enrolment/masterstudy/"
)
APPLICATION_URL = CATALOG_URL
DEGREE_RE = re.compile(
    r"(?:LL\.M\.|M\.(?:A|Sc|Ed|Eng|Res|Phil|B\.A|F\.A|L\.M)\.|M[A-Z][A-Za-z.]*)"
)


class WurzburgAdapter(OfficialCatalogAdapter):
    university_id = "university-of-wurzburg"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "wurzburg"
    institution_name = "University of Würzburg"
    minimum_expected_programmes = 85
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-central-masters-application-table"
    catalogue_limitation_reason = (
        "Würzburg's official central table systematically covers master's "
        "programmes, intakes, and application periods. Most opening descriptions "
        "are imprecise phrases such as 'end of May', so they remain monitored "
        "policy text instead of being coerced into exact dates."
    )

    def __init__(self, minimum_expected_programmes: int = 85) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for table_row in soup.select("table tr"):
            cells = table_row.select("td")
            if len(cells) < 4:
                continue
            label = normalise(cells[0].get_text(" ", strip=True))
            if not label:
                continue
            folded = label.casefold()
            if folded.startswith("master's programmes") or "qualification" in folded:
                continue
            degree_match = DEGREE_RE.search(label)
            degree_type = degree_match.group(0) if degree_match else "Master"
            name = label
            if degree_match is not None:
                if degree_match.start() == 0:
                    opening = label.find("(", degree_match.end())
                    if opening >= 0:
                        name = label[:opening].rstrip()
                else:
                    opening = label.rfind("(", 0, degree_match.start())
                    if opening >= 0:
                        name = label[:opening].rstrip()
                    else:
                        name = label[: degree_match.start()].rstrip(" ,(")
                        name = re.sub(r",?\s*\d+(?:/\d+)?\s*,?\s*$", "", name)
            link = cells[0].select_one("a[href]")
            source_url = (
                urljoin(CATALOG_URL, str(link["href"]))
                if link is not None
                else CATALOG_URL
            )
            hostname = (urlparse(source_url).hostname or "").casefold()
            if hostname != "uni-wuerzburg.de" and not hostname.endswith(
                ".uni-wuerzburg.de"
            ):
                source_url = CATALOG_URL
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree_type,
                    source_url=source_url,
                )
            )
        return rows
