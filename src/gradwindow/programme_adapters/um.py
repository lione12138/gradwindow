from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)

UNIVERSITY_ID = "universiti-malaya-um"
CATALOG_URL = "https://study.um.edu.my/pg-faculties"
DEADLINES_URL = "https://study.um.edu.my/how-to-apply"
APPLICATION_URL = "https://apply.um.edu.my"


class UMAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "official"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 125) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        root = BeautifulSoup(fetcher(CATALOG_URL), "html.parser")
        faculty_pages: dict[str, str] = {}
        for link in root.select('a[href*="pg-"]'):
            href = str(link.get("href", ""))
            if href.endswith("pg-faculties"):
                continue
            url = urljoin(CATALOG_URL, href)
            faculty_pages[url] = " ".join(link.stripped_strings).title()
        policies = _policies(fetcher(DEADLINES_URL))
        programmes: dict[str, DiscoveredProgramme] = {}
        for url, faculty in faculty_pages.items():
            soup = BeautifulSoup(fetcher(url), "html.parser")
            for card in soup.select(".course-card"):
                link = card.select_one("a[href]")
                if link is None:
                    continue
                name = " ".join(link.stripped_strings)
                if not re.match(r"^(Master|MBA|MSc)\b", name, re.I):
                    continue
                source_url = urljoin(url, str(link.get("href", "")))
                mode = (
                    "research"
                    if "research" in card.get("class", []) or "research" in source_url
                    else "coursework"
                )
                window = policies[mode]
                programme_id = f"um-{_slug(name)}"
                if name == "Master of Computer Science (Applied Computing)":
                    programme_id = "um-computer-science-applied-computing-master"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=_degree_type(name),
                    faculty=faculty,
                    department=faculty,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[window],
                    deadline_text="Universiti Malaya's official application calendar publishes exact postgraduate opening and closing dates by programme mode.",
                    parse_status="parsed",
                    retrieval_method="official-faculty-directory",
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Universiti Malaya catalogue contained {len(result)} master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _policies(html: str) -> dict[str, DiscoveredWindow]:
    soup = BeautifulSoup(html, "html.parser")
    rows = [" ".join(row.stripped_strings) for row in soup.select("table tr")]
    postgraduate = [row for row in rows if "POSTGRADUATE" in row]
    coursework = next((row for row in postgraduate if "Mixed Mode" in row), "")
    research = next(
        (row for row in postgraduate if "Mode of Programme: * Research" in row), ""
    )
    return {
        "coursework": _window(coursework, "October 2026", "Coursework and mixed mode"),
        "research": _window(research, "October 2026", "Research mode"),
    }


def _window(text: str, intake: str, round_name: str) -> DiscoveredWindow:
    dates = re.findall(
        r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec) \d{4}\b",
        text,
    )
    if len(dates) < 2:
        raise ValueError(f"Universiti Malaya {round_name} policy lacks exact dates")
    parsed = [
        datetime.strptime(value.replace("Sept", "Sep"), "%d %b %Y").date().isoformat()
        for value in dates[:2]
    ]
    return DiscoveredWindow(
        round=round_name,
        opens_at=parsed[0],
        closes_at=parsed[1],
        intake=intake,
        source_url=DEADLINES_URL,
    )


def _degree_type(name: str) -> str:
    if name.startswith(("MBA", "MSc")):
        return name.split()[0]
    match = re.match(r"Master of ([A-Za-z]+)", name)
    return (
        f"M{match.group(1)[0]}"
        if match and match.group(1) in {"Arts", "Science"}
        else "Master"
    )


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
