from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.queensu.ca/grad-postdoc/grad-studies/programs-degrees"
APPLICATION_URL = "https://www.queensu.ca/grad-postdoc/grad-studies/apply"
BUSINESS_URL = "https://smith.queensu.ca/grad_studies/"

_DEGREE_PREFIXES = (
    ("MNPHCNP", "MN(PHCNP)"),
    ("MSCOT", "MSc OT"),
    ("MSCPT", "MSc PT"),
    ("MHPE", "MHPE"),
    ("MMSC", "MMSc"),
    ("MNSC", "MNSc"),
    ("MEERL", "MEERL"),
    ("MPHIL", "MPhil"),
    ("PMIR", "PMIR"),
    ("MASC", "MASc"),
    ("MENG", "MEng"),
    ("MPH", "MPH"),
    ("MAC", "MAC"),
    ("MBI", "MBI"),
    ("MES", "MES"),
    ("MIR", "MIR"),
    ("MPA", "MPA"),
    ("MPL", "MPL"),
    ("LLM", "LLM"),
    ("MED", "MEd"),
    ("PME", "PME"),
    ("MSC", "MSc"),
    ("MA", "MA"),
)


class QueensOntarioAdapter(BaseProgrammeAdapter):
    university_id = "queen-s-university-ontario"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 75

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for table in soup.select("table"):
            heading = table.find_previous(["h2", "h3", "h4"])
            faculty = (
                normalise(heading.get_text(" ", strip=True))
                if heading is not None
                else "Queen's University"
            )
            for row in table.select("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                source = cells[0].select_one("a[href]")
                if source is None:
                    continue
                name = normalise(cells[0].get_text(" ", strip=True))
                source_url = urljoin(CATALOG_URL, str(source.get("href", "")))
                if not _is_queens_url(source_url):
                    source_url = CATALOG_URL
                for degree_type in _master_degrees(cells[1].get_text(" ", strip=True)):
                    programme_id = f"queens-ontario-{slug(name)}-{slug(degree_type)}"
                    programmes[programme_id] = _programme(
                        programme_id=programme_id,
                        name=name,
                        degree_type=degree_type,
                        faculty=faculty,
                        source_url=source_url,
                    )

        business_text = next(
            (
                normalise(node.get_text(" ", strip=True))
                for node in soup.find_all("p")
                if "Master of Business Administration" in node.get_text(" ")
            ),
            "",
        )
        for title in re.findall(
            r"Master of [^,.]+(?: & [^,.]+)?",
            business_text,
        ):
            name = normalise(title)
            programme_id = f"queens-ontario-{slug(name)}-master"
            programmes[programme_id] = _programme(
                programme_id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Smith School of Business",
                source_url=BUSINESS_URL,
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Queen's official directory contained "
                f"{len(result)} master's programme-and-degree entries; expected "
                f"at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _master_degrees(value: str) -> list[str]:
    result = []
    for segment in normalise(value).split(","):
        if "/" in segment:
            continue
        compact = re.sub(r"[^A-Za-z]", "", segment).upper()
        degree = next(
            (
                canonical
                for prefix, canonical in _DEGREE_PREFIXES
                if compact.startswith(prefix)
            ),
            None,
        )
        if degree is not None:
            result.append(degree)
    return result


def _programme(
    *,
    programme_id: str,
    name: str,
    degree_type: str,
    faculty: str,
    source_url: str,
) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type=degree_type,
        faculty=faculty,
        department=faculty,
        source_url=source_url,
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text=(
            "Queen's official application guide says the portal typically opens "
            "in September, while exact deadlines are programme-specific. Because "
            "it does not publish a complete pair of exact dates here, no dates are "
            "inferred."
        ),
        parse_status="no-deadline",
        retrieval_method="official-graduate-programme-and-degree-directory",
        evidence_quality="official-full-text",
    )


def _is_queens_url(value: str) -> bool:
    host = (urlparse(value).hostname or "").lower()
    return host == "queensu.ca" or host.endswith(".queensu.ca")
