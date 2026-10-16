"""Reviewed deadline-only facts, deliberately separate from application windows."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field

from .discovery import same_official_domain
from .io import read_json, write_json
from .models import DataModel
from .paths import APPLICANT_CATEGORIES_PATH, PROGRAMS_PATH, ROOT, UNIVERSITIES_PATH

REVIEWED_DEADLINES_PATH = ROOT / "data" / "reviewed-deadlines.json"


class DeadlineEvidence(DataModel):
    source_url: AnyHttpUrl = Field(alias="sourceUrl")
    excerpt: str = Field(min_length=10)


class ReviewedDeadline(DataModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    university_id: str = Field(alias="universityId")
    programme_id: str = Field(alias="programmeId")
    intake: str = Field(min_length=4)
    round: str = Field(min_length=1)
    applicant_categories: list[str] = Field(alias="applicantCategories", min_length=1)
    closes_at: date = Field(alias="closesAt")
    deadline_semantics: Literal["on", "before"] = Field(
        default="on", alias="deadlineSemantics"
    )
    opens_at: None = Field(default=None, alias="opensAt")
    data_status: Literal["deadline-only"] = Field(
        default="deadline-only", alias="dataStatus"
    )
    source_url: AnyHttpUrl = Field(alias="sourceUrl")
    verified_at: date = Field(alias="verifiedAt")
    reviewed_by: str = Field(alias="reviewedBy", min_length=1)
    evidence: list[DeadlineEvidence] = Field(min_length=1)


def validate_reviewed_deadlines(payload, universities, programmes, categories):
    errors = []
    schools = {item["id"]: item for item in universities}
    programmes = {item["id"]: item for item in programmes}
    category_ids = {item["id"] for item in categories}
    seen = set()
    seen_scopes = set()
    if not isinstance(payload, dict) or not isinstance(payload.get("deadlines"), list):
        return ["reviewed deadlines must contain a deadlines list"]
    for item in payload["deadlines"]:
        try:
            record = ReviewedDeadline.model_validate(item)
        except ValueError as exc:
            errors.append(f"reviewed deadline: {exc}")
            continue
        label = record.id
        if label in seen:
            errors.append(f"{label}: duplicate deadline")
        seen.add(label)
        scope = (
            record.programme_id,
            record.intake,
            record.round,
            tuple(sorted(record.applicant_categories)),
        )
        if scope in seen_scopes:
            errors.append(f"{label}: duplicate or conflicting deadline scope")
        seen_scopes.add(scope)
        school = schools.get(record.university_id)
        programme = programmes.get(record.programme_id)
        if (
            not school
            or not programme
            or programme["universityId"] != record.university_id
        ):
            errors.append(f"{label}: unknown or mismatched school/programme")
            continue
        urls = [str(record.source_url), *(str(e.source_url) for e in record.evidence)]
        if any(
            not same_official_domain(url, school["officialDomains"]) for url in urls
        ):
            errors.append(f"{label}: evidence must use official university domains")
        if str(record.source_url) not in [str(e.source_url) for e in record.evidence]:
            errors.append(f"{label}: deadline source has no evidence")
        if not set(record.applicant_categories) <= category_ids:
            errors.append(f"{label}: unknown applicant category")
        if record.verified_at > date.today() or not record.reviewed_by.strip():
            errors.append(f"{label}: invalid verification date or reviewer")
    return errors


def load_reviewed_deadlines(path: Path | None = None):
    payload = read_json(path or REVIEWED_DEADLINES_PATH)
    errors = validate_reviewed_deadlines(
        payload,
        read_json(UNIVERSITIES_PATH)["universities"],
        read_json(PROGRAMS_PATH)["programs"],
        read_json(APPLICANT_CATEGORIES_PATH)["categories"],
    )
    if errors:
        raise ValueError("\n".join(errors))
    return payload


def approve_deadline_file(draft_path: Path, reviewer: str):
    """Explicit reviewer action only; discovery adapters never call this."""
    draft = read_json(draft_path)
    draft["reviewedBy"] = reviewer
    record = ReviewedDeadline.model_validate(draft).model_dump(
        mode="json", by_alias=True
    )
    payload = load_reviewed_deadlines()
    if any(item["id"] == record["id"] for item in payload["deadlines"]):
        raise ValueError(
            "Deadline already exists; review changes explicitly before replacing it"
        )
    payload["deadlines"].append(record)
    errors = validate_reviewed_deadlines(
        payload,
        read_json(UNIVERSITIES_PATH)["universities"],
        read_json(PROGRAMS_PATH)["programs"],
        read_json(APPLICANT_CATEGORIES_PATH)["categories"],
    )
    if errors:
        raise ValueError("\n".join(errors))
    write_json(REVIEWED_DEADLINES_PATH, payload)
    return record
