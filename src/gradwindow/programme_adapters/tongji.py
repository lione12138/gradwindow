from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)
from .official_catalog import normalise

CATALOG_URL = "https://study.tongji.edu.cn/en/info/1014/1044.htm"
APPLICATION_URL = "https://study-info.tongji.edu.cn/"


class TongjiAdapter(BaseProgrammeAdapter):
    university_id = "tongji-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Fall 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 1

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
        intake_match = re.search(r"Fall\s+(20\d{2})\s+\(August/September\)", text)
        if intake_match is None or "Applicants for a master’s program" not in text:
            raise ValueError("Tongji's current international master's guide is missing")
        intake = f"Fall {intake_match.group(1)}"
        rounds = (
            (
                "Chinese Government Scholarship and first self-funded round",
                "Chinese Government Scholarship",
            ),
            (
                "Shanghai Municipal Scholarship and self-funded round",
                "Shanghai Municipal Government Scholarship",
            ),
        )
        windows = []
        for round_name, label in rounds:
            match = re.search(
                re.escape(label)
                + r".*?self-funded:\s*"
                + r"(?P<opens>[A-Z][a-z]+\s+\d{1,2},\s+20\d{2})\s*[-–—]\s*"
                + r"(?P<closes>[A-Z][a-z]+\s+\d{1,2},\s+20\d{2})",
                text,
                re.I,
            )
            if match is None:
                raise ValueError(f"Tongji's official guide lacks dates for {label}")
            opens_at = datetime.strptime(match.group("opens"), "%B %d, %Y").date()
            closes_at = datetime.strptime(match.group("closes"), "%B %d, %Y").date()
            windows.append(
                DiscoveredWindow(
                    round=round_name,
                    intake=intake,
                    applicant_categories=["international-students"],
                    opens_at=opens_at.isoformat(),
                    closes_at=closes_at.isoformat(),
                    source_url=CATALOG_URL,
                )
            )

        programme = DiscoveredProgramme(
            id="tongji-international-masters-admissions",
            name="International master's admissions",
            degree_type="Master",
            faculty="International Students Office",
            department="English-taught master's programmes",
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=windows,
            deadline_text=(
                "Tongji's official 2026 international master's enrollment guide "
                "publishes two Fall 2026 application rounds with exact opening and "
                "closing dates. The attached major workbook requires an interactive "
                "download check, so exact dates are kept on this explicit school-level "
                "master's scope rather than copied to individual majors."
            ),
            parse_status="parsed",
            retrieval_method="official-international-masters-enrollment-guide",
            evidence_quality="official-full-text",
        )
        return DiscoveredCatalog(
            application_opens_at=min(window.opens_at for window in windows),
            programmes=[programme],
        )
