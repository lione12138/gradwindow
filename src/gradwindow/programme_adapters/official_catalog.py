from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urljoin

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme

MASTER_DEGREE_RE = re.compile(
    r"\b(LLM|MBA|MArch|MASt|MASc|MCAAM|MCEE|MChE|MCS|MDS|MECE|MEd|MEML|MEng|MFA|MFin|MIE|MIS|MME|MMus|MPhil|MPH|MRes|MSc|MStat|MS|MA|Master)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    name: str
    degree_type: str
    source_url: str


class OfficialCatalogAdapter(BaseProgrammeAdapter):
    """Shared publication-safe behaviour for official catalogue adapters."""

    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    intake = "Varies by programme"
    minimum_expected_programmes = 1
    school_prefix = ""
    institution_name = ""
    retrieval_method = "official-course-catalogue"

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        return self._catalog(self.extract_entries(html))

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        raise NotImplementedError

    def _catalog(self, entries: list[CatalogEntry]) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for entry in entries:
            name = normalise(entry.name)
            degree_type = normalise(entry.degree_type)
            source_url = entry.source_url.strip()
            if not name or not degree_type or not source_url:
                continue
            programme_id = f"{self.school_prefix}-{slug(name)}-{slug(degree_type)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=self.institution_name,
                department=self.institution_name,
                source_url=source_url,
                application_url=self.application_url,
                windows=[],
                deadline_text=(
                    "Programme found in the official university catalogue. "
                    "No official programme-specific pair of exact opening and "
                    "closing dates was published, so no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"{self.university_id} catalogue contained {len(result)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def entry(
    *,
    name: str,
    degree_type: str,
    source_url: str,
    base_url: str,
) -> CatalogEntry:
    return CatalogEntry(
        name=normalise(name),
        degree_type=normalise(degree_type),
        source_url=urljoin(base_url, source_url.strip()),
    )


def degree_from(value: str, default: str = "Master") -> str:
    match = MASTER_DEGREE_RE.search(value)
    return match.group(1) if match else default


def normalise(value: str) -> str:
    return " ".join(str(value).replace("\u00a0", " ").split())


def slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip(
        "-"
    )
