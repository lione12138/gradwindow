from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher, OfficialSourceTransportError
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.qub.ac.uk/courses/postgraduate-taught/"
JANUARY_PROGRAMMES_URL = (
    "https://www.qub.ac.uk/Study/postgraduate/january-intake/courses/"
)
APPLICATION_PORTAL_URL = (
    "https://myportal.qub.ac.uk/SignIn?ReturnUrl=%2Fpg-admission-application-list%2F"
)

MASTER_QUALIFICATIONS = {
    "LLM",
    "MA",
    "MArch",
    "MBA",
    "MEd",
    "MLaw",
    "MPH",
    "MRes",
    "MSc",
    "MSc(Res)",
}
_JANUARY_ROUTE_RE = re.compile(
    r"^(?P<degree>MSc(?:\(Res\))?|MArch|MRes|MLaw|MEd|MBA|MPH|LLM|MA)"
    r"(?:\s+(?P<name>.+))?$",
    re.I,
)


class QUBAdapter(OfficialCatalogAdapter):
    """Discover Queen's Belfast PGT identities and January intake status."""

    university_id = "queen-s-university-belfast"
    school_prefix = "qub"
    institution_name = "Queen's University Belfast"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_PORTAL_URL
    window_watch_urls = (JANUARY_PROGRAMMES_URL,)
    retrieval_method = "official-course-catalogue"
    browser_fallback_limit = 2

    def __init__(
        self,
        minimum_expected_programmes: int = 130,
        minimum_expected_january: int = 14,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.minimum_expected_january = minimum_expected_january

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue_document = fetcher(CATALOG_URL)
        january_document = fetcher(JANUARY_PROGRAMMES_URL)
        _reject_access_challenge(catalogue_document)
        _reject_access_challenge(january_document)
        catalog = self.parse_catalog(catalogue_document)
        intake, january_routes = _january_routes(january_document)
        if len(january_routes) < self.minimum_expected_january:
            raise ValueError(
                f"QUB's official page contained {len(january_routes)} {intake} "
                f"programmes; expected at least {self.minimum_expected_january}"
            )

        programme_routes = {
            _route_key(programme.name, programme.degree_type): programme
            for programme in catalog.programmes
        }
        unmatched = sorted(january_routes - set(programme_routes))
        if unmatched:
            raise ValueError(
                "QUB's January programme list did not match the main catalogue: "
                f"{unmatched[:3]}"
            )
        for route in january_routes:
            programme = programme_routes[route]
            programme.available_intakes = [intake]
            programme.application_status = "open"
            programme.deadline_text = (
                f"QUB's official {intake} page lists this programme with an "
                "Apply now action, but publishes no exact opening or closing date."
            )
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        _reject_access_challenge(html)
        return self._catalog(self.extract_entries(html))

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for card in soup.select("ul.course-listing > li"):
            link = card.select_one("h4 a[href]")
            qualification_node = link.select_one("span") if link else None
            if link is None or qualification_node is None:
                continue
            degree_type = normalise(qualification_node.get_text(" ", strip=True))
            if degree_type not in MASTER_QUALIFICATIONS:
                continue
            full_name = normalise(link.get_text(" ", strip=True))
            name = (
                full_name[: -len(degree_type)].strip()
                if full_name.endswith(degree_type)
                else full_name
            )
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_type,
                    source_url=urljoin(CATALOG_URL, link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _january_routes(document: str) -> tuple[str, set[tuple[str, str]]]:
    soup = BeautifulSoup(document, "html.parser")
    text = normalise(soup.get_text(" ", strip=True))
    intake_match = re.search(r"January\s+(20\d{2})", text, re.I)
    if intake_match is None:
        raise ValueError("QUB's official January intake year was not found")
    intake = f"January {intake_match.group(1)}"
    routes = set()
    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if (
            len(cells) < 2
            or "apply now" not in cells[1].get_text(" ", strip=True).lower()
        ):
            continue
        label = normalise(cells[0].get_text(" ", strip=True))
        match = _JANUARY_ROUTE_RE.fullmatch(label)
        if match is None:
            continue
        degree_type = _canonical_degree(match.group("degree"))
        name = normalise(match.group("name") or degree_type)
        if degree_type == "MBA" and name.casefold().startswith("with "):
            name = f"MBA {name}"
        routes.add(_route_key(name, degree_type))
    return intake, routes


def _route_key(name: str, degree_type: str) -> tuple[str, str]:
    value = name.casefold().replace("master of business administration", "mba")
    value = re.sub(r"\((?:ai|ft|pt|full[ -]?time|part[ -]?time)\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split()), degree_type.casefold()


def _canonical_degree(value: str) -> str:
    lowered = value.casefold()
    return next(
        degree for degree in MASTER_QUALIFICATIONS if degree.casefold() == lowered
    )


def _reject_access_challenge(document: str) -> None:
    lowered = document[:10_000].lower()
    if any(
        marker in lowered
        for marker in (
            "awswafcookiedomainlist",
            "request could not be satisfied",
            "generated by cloudfront",
        )
    ):
        raise OfficialSourceTransportError(
            "QUB official source returned an access challenge instead of catalogue data"
        )
