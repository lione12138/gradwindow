from __future__ import annotations

import hashlib
from collections.abc import Callable

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import slug

GUIDE_URL = "https://en.uestc.edu.cn/UESTC_Admission_Brochure-EN.pdf"
APPLICATION_URL = "http://admission.uestc.edu.cn/"
EXPECTED_GUIDE_SHA256 = (
    "cd4ea8f64f11474c569dcd6dd9a38960ccbc8fe9ae4a606ec59d066396418d70"
)

GuideHashFetcher = Callable[[str], str]

# The star-marked master's column on page 5 was visually reviewed on 2026-08-12.
# The PDF hash below prevents this transcription from surviving a changed brochure.
MASTER_PROGRAMMES = (
    "Electronic Science and Technology",
    "Information and Communication Engineering",
    "Computer Science and Technology",
    "Optical Engineering",
    "Software Engineering",
    "Biomedical Engineering",
    "Mechanical Engineering",
    "Instrument Science and Technology",
    "Control Science and Engineering",
    "Materials Science and Engineering",
    "Electrical Engineering",
    "Physics",
    "Mathematics",
    "Public Management",
    "Foreign Language and Literature",
)


class UESTCAdapter:
    university_id = "university-of-electronic-science-and-technology-of-china"
    catalog_url = GUIDE_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (GUIDE_URL,)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "uestc-international-graduate-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 15,
        maximum_expected_programmes: int = 15,
        guide_hash_fetcher: GuideHashFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.guide_hash_fetcher = guide_hash_fetcher or _fetch_guide_hash

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        guide_hash = self.guide_hash_fetcher(GUIDE_URL)
        if guide_hash != EXPECTED_GUIDE_SHA256:
            raise ValueError(
                "UESTC's 2026 brochure changed; its visually verified master's "
                "programme column requires fresh review"
            )
        programmes = [_programme(name, guide_hash) for name in MASTER_PROGRAMMES]
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"UESTC brochure contained {len(programmes)} English-taught "
                "master's programmes; expected "
                f"{self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        programmes.append(_admission_group(guide_hash))
        return DiscoveredCatalog(
            application_opens_at="2025-12-01",
            programmes=programmes,
        )


def _programme(name: str, guide_hash: str) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id=f"uestc-{slug(name)}-master",
        name=name,
        degree_type="Master",
        faculty="University of Electronic Science and Technology of China",
        department="University of Electronic Science and Technology of China",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text=(
            "Programme is marked as an English-taught master's programme in "
            "UESTC's official 2026 admissions brochure. The common exact "
            "application period is represented once at programme-group scope."
        ),
        parse_status="no-deadline",
        retrieval_method="official-2026-brochure-visually-verified",
        evidence_quality="official-full-text",
        evidence_document_hash=guide_hash,
    )


def _admission_group(guide_hash: str) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id="uestc-international-graduate-admissions",
        name="International graduate admissions",
        degree_type="Master/Doctoral",
        faculty="School of International Education",
        department="School of International Education",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=[
            DiscoveredWindow(
                round="Autumn international graduate admissions",
                applicant_categories=["international-students"],
                opens_at="2025-12-01",
                closes_at="2026-03-01",
                intake="Autumn 2026",
                source_url=GUIDE_URL,
                opens_at_basis="official",
            )
        ],
        deadline_text=(
            "UESTC's official 2026 brochure publishes the exact autumn "
            "graduate application period December 1, 2025 to March 1, 2026."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-brochure-visually-verified",
        evidence_quality="official-full-text",
        evidence_document_hash=guide_hash,
    )


def _fetch_guide_hash(url: str) -> str:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=120,
        max_bytes=20_000_000,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("UESTC source did not return its bounded official PDF")
    return hashlib.sha256(page.raw_bytes).hexdigest()
