from __future__ import annotations

import re
from collections.abc import Callable
from io import BytesIO

from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import slug

CATALOG_URL = "https://www.lshtm.ac.uk/files/pg_prospectus.pdf"
APPLICATION_URL = "https://www.lshtm.ac.uk/study/applications"

PROGRAMMES = (
    "MSc Climate Change & Planetary Health",
    "MSc Climate Change & Planetary Health (online)",
    "MSc Clinical Trials",
    "MSc Control of Infectious Diseases",
    "MSc Demography & Health",
    "MSc Demography & Health (online)",
    "MSc Epidemiology",
    "MSc Epidemiology by Distance Learning",
    "MSc Global Health Policy",
    "MSc Global Mental Health",
    "MSc Health Data Science",
    "MSc Health in Humanitarian Crises",
    "MSc Health Policy, Planning & Financing",
    "MSc Immunology of Infectious Diseases",
    "MSc Infectious Diseases",
    "MSc Medical Microbiology",
    "MSc Medical Parasitology & Entomology",
    "MSc Medical Statistics",
    "MSc Nutrition for Global Public Health",
    "MSc One Health: Ecosystems, Humans and Animals",
    "MSc Public Health",
    "MSc Public Health for Eye Care",
    "MSc Public Health for Global Practice",
    "MSc Reproductive & Sexual Health Research",
    "MSc Sexual & Reproductive Health Policy and Programming (online)",
    "MSc Tropical Medicine & International Health",
    "MSc Veterinary Epidemiology",
)

ProspectusTextFetcher = Callable[[str], str]


class LSHTMAdapter:
    university_id = "london-school-of-hygiene-and-tropical-medicine"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = ()
    catalogue_status = "partial"
    retrieval_method = "official-2026-27-postgraduate-prospectus"
    catalogue_limitation_reason = (
        "LSHTM's official 2026-27 prospectus confirms the taught master's routes "
        "emitted here, but does not enumerate every distance-learning route in its "
        "course profiles. Applications and deadlines vary by route, so month-only "
        "guidance is not converted into exact dates."
    )

    def __init__(
        self,
        expected_programmes: tuple[str, ...] = PROGRAMMES,
        prospectus_text_fetcher: ProspectusTextFetcher | None = None,
    ) -> None:
        self.expected_programmes = expected_programmes
        self.prospectus_text_fetcher = prospectus_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        del fetcher
        text = self.prospectus_text_fetcher(CATALOG_URL)
        compact = _compact(text)
        missing = [
            title for title in self.expected_programmes if not _present(title, compact)
        ]
        if missing:
            raise ValueError(
                "LSHTM prospectus no longer confirms the expected taught master's "
                f"portfolio: {', '.join(missing[:3])}"
            )
        programmes = []
        for title in self.expected_programmes:
            degree_type, name = title.split(" ", 1)
            programme_id = f"lshtm-{slug(name)}-{degree_type.casefold()}"
            programmes.append(
                DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree_type,
                    faculty="London School of Hygiene & Tropical Medicine",
                    department="London School of Hygiene & Tropical Medicine",
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Programme is confirmed by LSHTM's official 2026-27 "
                        "postgraduate prospectus. No programme-specific exact "
                        "opening and closing date pair is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _present(title: str, compact_text: str) -> bool:
    variants = {
        "MSc Clinical Trials": "clinicaltrialsdesignedto",
        "MSc Health in Humanitarian Crises": "healthinhumanitariancrises",
        "MSc Infectious Diseases": "infectiousdiseasesdesignedto",
        "MSc One Health: Ecosystems, Humans and Animals": (
            "onehealthecosystemshumansanimals"
        ),
    }
    needle = variants.get(title, _compact(title))
    return needle in compact_text


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _fetch_pdf_text(url: str) -> str:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=90,
        max_bytes=1_500_000,
        accept="application/pdf,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("LSHTM prospectus did not return a bounded PDF")
    reader = PdfReader(BytesIO(page.raw_bytes))
    if not 20 <= len(reader.pages) <= 25:
        raise ValueError("LSHTM prospectus page count changed unexpectedly")
    return "\n".join(page.extract_text() or "" for page in reader.pages)
