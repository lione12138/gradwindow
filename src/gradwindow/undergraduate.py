from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, TypeAdapter, model_validator

from .discovery import same_official_domain
from .io import read_json
from .models import SLUG_PATTERN, DataModel
from .paths import ROOT, UNIVERSITIES_PATH

UNDERGRADUATE_PATH = ROOT / "data" / "undergraduate-applications.json"
ADMISSIONS_PLATFORM_DOMAINS = ["ucas.com", "commonapp.org"]


class UndergraduateWindow(DataModel):
    id: str = Field(pattern=SLUG_PATTERN)
    university_id: str = Field(alias="universityId", pattern=SLUG_PATTERN)
    scope: str = Field(min_length=1)
    scope_zh: str = Field(alias="scopeZh", min_length=1)
    intake: str = Field(min_length=4)
    intake_zh: str = Field(alias="intakeZh", min_length=4)
    applicant_scope: Literal["international", "international-and-domestic"] = Field(
        alias="applicantScope"
    )
    round: Literal[
        "standard",
        "equal-consideration",
        "restrictive-early-action",
        "early-decision",
        "regular-decision",
    ]
    opens_at: date = Field(alias="opensAt")
    closes_at: date = Field(alias="closesAt")
    source_url: AnyHttpUrl = Field(alias="sourceUrl")
    opening_source_url: AnyHttpUrl = Field(alias="openingSourceUrl")
    eligibility_source_url: AnyHttpUrl = Field(alias="eligibilitySourceUrl")
    application_url: AnyHttpUrl = Field(alias="applicationUrl")
    verified_at: date = Field(alias="verifiedAt")
    evidence: str = Field(min_length=10)

    @model_validator(mode="after")
    def validate_dates(self) -> UndergraduateWindow:
        if self.opens_at > self.closes_at:
            raise ValueError("opensAt is after closesAt")
        if self.verified_at > date.today():
            raise ValueError("verifiedAt cannot be in the future")
        return self


WINDOWS = TypeAdapter(list[UndergraduateWindow])


def load_undergraduate_windows(path: Path = UNDERGRADUATE_PATH) -> list[dict]:
    schools = {
        school["id"]: school for school in read_json(UNIVERSITIES_PATH)["universities"]
    }
    windows = WINDOWS.validate_python(read_json(path))
    seen_ids: set[str] = set()
    seen_scopes: set[tuple[str, str, str, str]] = set()
    result = []
    for window in windows:
        scope = (window.university_id, window.scope, window.intake, window.round)
        if window.id in seen_ids or scope in seen_scopes:
            raise ValueError(f"{window.id}: duplicate undergraduate window")
        seen_ids.add(window.id)
        seen_scopes.add(scope)
        school = schools.get(window.university_id)
        if school is None:
            raise ValueError(f"{window.id}: unknown university")
        domains = school["officialDomains"]
        if any(
            not same_official_domain(str(url), domains)
            for url in (window.source_url, window.eligibility_source_url)
        ):
            raise ValueError(
                f"{window.id}: expected university deadline and eligibility sources"
            )
        if any(
            not same_official_domain(str(url), [*domains, *ADMISSIONS_PLATFORM_DOMAINS])
            for url in (window.opening_source_url, window.application_url)
        ):
            raise ValueError(
                f"{window.id}: expected official opening and application links"
            )
        result.append(
            {
                **window.model_dump(mode="json", by_alias=True),
                **{
                    key: school.get(key)
                    for key in (
                        "school",
                        "schoolZh",
                        "country",
                        "qsRank",
                        "rankDisplay",
                    )
                },
            }
        )
    return result
