from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup, Tag
from pydantic import AnyHttpUrl, Field, model_validator

from .discovery import same_official_domain
from .http_client import DEFAULT_USER_AGENT, FetchedPage, FetchFailure, fetch_page
from .io import read_json
from .models import SLUG_PATTERN, DataModel
from .paths import ROOT, UNIVERSITIES_PATH
from .undergraduate import UNDERGRADUATE_PATH, UndergraduateWindow

UCAS_CONFIG_PATH = ROOT / "data" / "ops" / "undergraduate-ucas-sources.json"
UCAS_DOMAINS = ["ucas.com"]
DATE_PATTERN = r"\d{1,2} [A-Za-z]+ \d{4}"


class UcasRoute(DataModel):
    university_id: str = Field(alias="universityId", pattern=SLUG_PATTERN)
    route_id: str = Field(alias="routeId", pattern=SLUG_PATTERN)
    scope: str = Field(min_length=1)
    scope_zh: str = Field(alias="scopeZh", min_length=1)
    applicant_scope: Literal["international", "international-and-domestic"] = Field(
        alias="applicantScope"
    )
    source_url: AnyHttpUrl = Field(alias="sourceUrl")
    eligibility_url: AnyHttpUrl = Field(alias="eligibilityUrl")
    application_url: AnyHttpUrl | None = Field(default=None, alias="applicationUrl")
    deadline_pattern: str = Field(alias="deadlinePattern", min_length=1)
    eligibility_pattern: str = Field(alias="eligibilityPattern", min_length=1)


class UcasSources(DataModel):
    entry_year: int = Field(alias="entryYear", ge=2020, le=2200)
    submission_event: AnyHttpUrl = Field(alias="submissionEvent")
    equal_consideration_event: AnyHttpUrl = Field(alias="equalConsiderationEvent")
    routes: list[UcasRoute] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_routes(self) -> UcasSources:
        if len({(route.university_id, route.route_id) for route in self.routes}) != len(
            self.routes
        ):
            raise ValueError("duplicate UCAS route")
        return self


def _fetch_html(url: str) -> FetchedPage:
    return fetch_page(url, user_agent=DEFAULT_USER_AGENT, max_bytes=4_000_000)


def _source_content(
    url: str, domains: list[str], fetcher: Callable[[str], FetchedPage]
) -> Tag:
    if not same_official_domain(url, domains):
        raise ValueError(f"source URL is outside the official domains: {url}")
    page = fetcher(url)
    if page.truncated or not same_official_domain(page.final_url, domains):
        raise ValueError(f"incomplete or off-domain source: {url}")
    soup = BeautifulSoup(page.body, "html.parser")
    content = soup.select_one("#main") or soup.find("main") or soup
    for element in content.select("script, style, noscript"):
        element.decompose()
    return content


def _text(element: Tag) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def _event_date(content: Tag, title_prefix: str, description_pattern: str) -> date:
    title = content.find("h1")
    if not title or not _text(title).lower().startswith(title_prefix):
        raise ValueError(f"UCAS event title does not match {title_prefix!r}")
    if not re.search(description_pattern, _text(content), re.I):
        raise ValueError(
            f"UCAS event lacks matching application guidance: {title_prefix}"
        )
    dates = {_text(element) for element in content.select(".header__list span")}
    dates = {value for value in dates if re.fullmatch(DATE_PATTERN, value)}
    if len(dates) != 1:
        raise ValueError(f"UCAS event has no unique exact date: {title_prefix}")
    return datetime.strptime(dates.pop(), "%d %B %Y").date()


def _route_record(
    route: UcasRoute,
    sources: UcasSources,
    opens: date,
    closes: date,
    deadline_text: str,
    eligibility_text: str,
) -> dict:
    if route.deadline_pattern.count("{date}") != 1:
        raise ValueError("deadline pattern needs one {date} placeholder")
    pattern = route.deadline_pattern.replace("{year}", str(sources.entry_year)).replace(
        "{date}", rf"(?P<date>{DATE_PATTERN})"
    )
    matches = list(re.finditer(pattern, deadline_text, re.I))
    published_dates = {
        datetime.strptime(match["date"], "%d %B %Y").date() for match in matches
    }
    if published_dates != {closes}:
        raise ValueError(
            "university deadline must match the exact UCAS equal-consideration deadline"
        )
    eligibility_match = re.search(route.eligibility_pattern, eligibility_text, re.I)
    if not eligibility_match:
        raise ValueError("no evidence that international applicants can use this route")

    year = sources.entry_year
    record = UndergraduateWindow.model_validate(
        {
            "id": f"{route.university_id}-{route.route_id}-{year}-equal-consideration",
            "universityId": route.university_id,
            "scope": route.scope,
            "scopeZh": route.scope_zh,
            "intake": f"Fall {year}",
            "intakeZh": f"{year} 年秋季",
            "applicantScope": route.applicant_scope,
            "round": "equal-consideration",
            "opensAt": opens,
            "closesAt": closes,
            "sourceUrl": route.source_url,
            "openingSourceUrl": sources.submission_event,
            "eligibilitySourceUrl": route.eligibility_url,
            "applicationUrl": route.application_url or route.source_url,
            "verifiedAt": date.today(),
            "evidence": f"Deadline: {matches[0].group()}. Eligibility: {eligibility_match.group()}.",
        }
    )
    return record.model_dump(mode="json", by_alias=True, exclude={"verified_at"})


def discover_undergraduate_ucas(
    sources: UcasSources,
    schools: list[dict],
    published: list[dict],
    *,
    fetcher: Callable[[str], FetchedPage] = _fetch_html,
) -> dict:
    """Check configured official routes and return review candidates only."""
    fetch_once = cache(fetcher)
    year = sources.entry_year
    opening_page = _source_content(
        str(sources.submission_event), UCAS_DOMAINS, fetch_once
    )
    deadline_page = _source_content(
        str(sources.equal_consideration_event), UCAS_DOMAINS, fetch_once
    )
    opens = _event_date(
        opening_page,
        f"{year} entry ucas applications can be submitted",
        r"send your completed application",
    )
    closes = _event_date(
        deadline_page,
        f"{year} entry deadline for all undergraduate courses",
        r"equal consideration",
    )
    if opens.year != year - 1 or closes.year != year or opens >= closes:
        raise ValueError("UCAS event dates do not fit the configured entry year")

    school_domains = {school["id"]: school["officialDomains"] for school in schools}
    published_by_id = {record["id"]: record for record in published}
    report = {"entryYear": year, "candidates": [], "needsReview": []}
    for route in sources.routes:
        try:
            domains = school_domains.get(route.university_id)
            if not domains:
                raise ValueError("unknown university or missing official domains")
            if route.application_url and not same_official_domain(
                str(route.application_url), [*domains, *UCAS_DOMAINS]
            ):
                raise ValueError(
                    "application URL must be on the university or UCAS domain"
                )
            source = _text(_source_content(str(route.source_url), domains, fetch_once))
            eligibility = (
                source
                if route.eligibility_url == route.source_url
                else _text(
                    _source_content(str(route.eligibility_url), domains, fetch_once)
                )
            )
            record = _route_record(route, sources, opens, closes, source, eligibility)
        except (FetchFailure, ValueError, re.error) as exc:
            report["needsReview"].append(
                {
                    "universityId": route.university_id,
                    "routeId": route.route_id,
                    "reason": str(exc),
                }
            )
            continue
        old = published_by_id.get(record["id"], {})
        unchanged = all(
            old.get(key) == value for key, value in record.items() if key != "evidence"
        )
        report["candidates"].append(
            {"reviewStatus": "unchanged" if unchanged else "pending", "record": record}
        )
    return report


def run_undergraduate_ucas_discovery(config_path: Path = UCAS_CONFIG_PATH) -> dict:
    return discover_undergraduate_ucas(
        UcasSources.model_validate(read_json(config_path)),
        read_json(UNIVERSITIES_PATH)["universities"],
        read_json(UNDERGRADUATE_PATH),
    )
