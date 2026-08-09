from __future__ import annotations

from .base import DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import OfficialCatalogAdapter

CATALOG_URL = "https://grad.msu.edu/departments"
DIRECTORY_URL = "https://admissions.msu.edu/academics/majors-degrees-programs"
APPLICATION_URL = "https://grad.msu.edu/admissions/apply"


class MichiganStateAdapter(OfficialCatalogAdapter):
    """Monitor MSU's client-rendered Sitecore programme directory."""

    university_id = "michigan-state-university"
    school_prefix = "michigan-state"
    institution_name = "Michigan State University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-sitecore-programme-directory-monitor"

    def extract_entries(self, html: str):  # pragma: no cover - custom catalogue
        raise NotImplementedError

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        if "Majors, degrees and programs" not in html or '"ProgramList"' not in html:
            raise ValueError("MSU programme directory markers changed unexpectedly")
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[
                DiscoveredProgramme(
                    id="msu-graduate-programmes",
                    name="Graduate programmes",
                    degree_type="Master/Doctoral",
                    faculty="The Graduate School",
                    department="The Graduate School",
                    source_url=DIRECTORY_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "MSU's official graduate directory is rendered from a "
                        "client-side Sitecore Search widget, while admissions "
                        "deadlines remain programme-specific. The directory is "
                        "monitored without inferring dates."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            ],
        )
