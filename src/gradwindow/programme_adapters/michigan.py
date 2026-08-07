from __future__ import annotations

import re

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://obp.umich.edu/wp-content/uploads/pubdata/almanac/"
    "Almanac_20th_Index_Appendix.pdf"
)
APPLICATION_URL = "https://rackham.umich.edu/admissions/applying/"

_FACULTIES = (
    "Taubman College of Architecture and Urban Planning (TAUP)",
    "Ross School of Business",
    "College of Engineering",
    "Law School",
    "Medical School",
    "School of Information",
    "School of Music, Theatre & Dance",
    "School of Public Health",
    "School of Social Work",
)


class MichiganAdapter(BaseProgrammeAdapter):
    university_id = "university-of-michigan-ann-arbor"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 15

    def parse_catalog(self, text: str) -> DiscoveredCatalog:
        start = text.find("Other Graduate Degree Programs")
        end = text.find("Professional Degree Programs", start)
        if start < 0 or end < 0:
            raise ValueError("Michigan Almanac's graduate degree appendix is missing")
        section = text[start:end]

        programmes: dict[str, DiscoveredProgramme] = {}
        positions = [
            (section.find(faculty), faculty)
            for faculty in _FACULTIES
            if section.find(faculty) >= 0
        ]
        positions.sort()
        for index, (position, faculty) in enumerate(positions):
            block_end = (
                positions[index + 1][0] if index + 1 < len(positions) else len(section)
            )
            block = section[position:block_end]
            display_faculty = faculty.removesuffix(" (TAUP)")
            for match in re.finditer(r"•\s+(Master(?:'s)?[^\r\n]+)", block):
                name = normalise(match.group(1))
                degree_match = re.search(r"\(([^()]+)\)\s*$", name)
                degree_type = degree_match.group(1) if degree_match else "Master"
                programme_id = f"michigan-non-rackham-{slug(name)}"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree_type,
                    faculty=display_faculty,
                    department=display_faculty,
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "The University of Michigan Office of Budget and Planning's "
                        "official Almanac appendix lists this Ann Arbor non-Rackham "
                        f"graduate degree under {display_faculty}. This adapter "
                        "currently covers the appendix's non-Rackham master's scope "
                        "because the Rackham programme table returns an unstable WAF "
                        "response to the monitor. The appendix does not publish exact "
                        "application dates, so no dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-michigan-almanac-appendix",
                    evidence_quality="official-full-text",
                )

        result = sorted(programmes.values(), key=lambda programme: programme.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Michigan's official Almanac appendix contained "
                f"{len(result)} non-Rackham master's offerings; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
