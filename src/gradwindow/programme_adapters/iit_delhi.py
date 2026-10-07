from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter, normalise

CATALOG_URL = "https://home.iitd.ac.in/pg-admissions.php"
APPLICATION_URL = "https://ecampus.iitd.ac.in/PGADM/"
CYCLE_RE = re.compile(r"\b20\d{2}[-–]([0-9]{2}|20\d{2})\b")


class IITDelhiAdapter(OfficialCatalogAdapter):
    """Monitor official PG announcements without inferring a programme catalogue."""

    university_id = "indian-institute-of-technology-delhi-iitd"
    school_prefix = "iitd"
    institution_name = "Indian Institute of Technology Delhi"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 1
    retrieval_method = "official-current-pg-admissions-monitor"
    catalogue_granularity = "admissions-route-level"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("script, style, header, nav, footer"):
            node.decompose()
        text = " ".join(soup.stripped_strings)
        pg_link = next(
            (
                link
                for link in soup.select("a[href]")
                if urlparse(str(link["href"])).scheme == "https"
                and urlparse(str(link["href"])).hostname == "ecampus.iitd.ac.in"
                and urlparse(str(link["href"])).path.rstrip("/")
                in {"/PGADM", "/PGADM/login", "/IPGADM/login"}
            ),
            None,
        )
        notices = [
            normalise(node.get_text(" ", strip=True))
            for node in soup.select("li")
            if "The admission portal for" in node.get_text(" ", strip=True)
            and "M.S." in node.get_text(" ", strip=True)
            and CYCLE_RE.search(node.get_text(" ", strip=True))
        ]
        legacy_brochure = any(
            "Information Brochure for Ph.D. and PG Admissions" in value
            and CYCLE_RE.search(value)
            for value in soup.stripped_strings
        )
        if (
            "ADMISSIONS" not in text
            or pg_link is None
            or not (notices or legacy_brochure)
        ):
            raise ValueError("IIT Delhi's current PG admissions route changed")
        guidance = (
            "Official admissions announcements (applicant categories remain separate): "
            + " | ".join(notices)
            if notices
            else "The official page links a Ph.D. and PG admissions brochure."
        )
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="iit-delhi-postgraduate-programmes",
                    name="Postgraduate programmes",
                    degree_type="Master",
                    faculty=self.institution_name,
                    department="Postgraduate admissions",
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        guidance + " This is an admissions-route monitor, not a "
                        "programme catalogue. Programme scope and complete dates "
                        "for each applicant category require brochure review; "
                        "no exact application window is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
