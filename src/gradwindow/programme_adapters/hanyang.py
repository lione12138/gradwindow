from __future__ import annotations

import re

from .base import DiscoveredCatalog
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = (
    "https://oia.hanyang.ac.kr/?act=procFileDownload&file_srl=1800349&"
    "module=file&module_srl=287&sid=ec2b33c333359a67956b4e02788d087c"
)
APPLICATION_URL = "https://oia.hanyang.ac.kr/admission"
PROGRAMME_RE = re.compile(
    r"((?:Department|School|The department)\s+of\s+.{2,180}?)([○X])\s*([○X])",
    re.IGNORECASE | re.DOTALL,
)


class HanyangAdapter(OfficialCatalogAdapter):
    """Read master's routes from Hanyang's official international guide."""

    university_id = "hanyang-university"
    school_prefix = "hanyang"
    institution_name = "Hanyang University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-admissions-guide"

    def __init__(self, minimum_expected_programmes: int = 80) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, text: str) -> DiscoveredCatalog:
        catalog = super().parse_catalog(text)
        for programme in catalog.programmes:
            if programme.name == "Department of Computer Science":
                programme.id = "hanyang-department-computer-science"
        return catalog

    def extract_entries(self, text: str) -> list[CatalogEntry]:
        if "Fields of Study" not in text:
            raise ValueError("Hanyang guide did not contain its Fields of Study")
        section = text.split("Fields of Study", 1)[1]
        if "Ⅲ." in section:
            section = section.split("Ⅲ.", 1)[0]
        entries = []
        for match in PROGRAMME_RE.finditer(section):
            if match.group(2) != "○":
                continue
            name = _clean_programme_name(match.group(1))
            if name:
                entries.append(
                    entry(
                        name=name,
                        degree_type="Master",
                        source_url=CATALOG_URL,
                        base_url=CATALOG_URL,
                    )
                )
        return entries


def _clean_programme_name(value: str) -> str:
    value = re.sub(r"\s*-\s*\d+\s*-\s*", " ", value)
    value = re.sub(r"\s+", " ", value)
    return normalise(value).strip(" -")
