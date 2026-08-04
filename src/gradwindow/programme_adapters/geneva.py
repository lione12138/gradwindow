from __future__ import annotations

import json

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise

CATALOG_URL = (
    "https://www.unige.ch/bachelor-master/api/unige_filter_cards/"
    "get_page_categories/74/en_GB/btUnigeFilterCards"
)
CATEGORY_URL = (
    "https://www.unige.ch/bachelor-master/api/unige_filter_cards/get_categories/en_GB"
)
APPLICATION_URL = "https://www.unige.ch/immatriculations/en/conditions"
MASTER_CATEGORY_ID = 273


class GenevaAdapter(BaseProgrammeAdapter):
    university_id = "university-of-geneva"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 90

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        cards = fetcher(CATALOG_URL)
        categories = fetcher(CATEGORY_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(cards, categories)

    def parse_catalog(
        self, cards_payload: str, categories_payload: str
    ) -> DiscoveredCatalog:
        cards = json.loads(cards_payload)
        category_groups = json.loads(categories_payload)
        if not isinstance(cards, list) or not isinstance(category_groups, list):
            raise ValueError("Geneva's official catalogue API returned invalid JSON")

        faculty_by_id = {
            value["id"]: normalise(value.get("text", ""))
            for group in category_groups
            if isinstance(group, dict)
            and group.get("title") == "Faculty / Institute / Center"
            for value in group.get("values", [])
            if isinstance(value, dict) and isinstance(value.get("id"), int)
        }
        programmes = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            category_ids = card.get("categories", [])
            if MASTER_CATEGORY_ID not in category_ids:
                continue
            record_id = card.get("id")
            name = normalise(card.get("name", ""))
            source_url = str(card.get("path", "")).strip()
            if (
                not isinstance(record_id, int)
                or not name
                or not source_url.startswith("https://www.unige.ch/")
            ):
                continue
            faculty = next(
                (faculty_by_id[item] for item in category_ids if item in faculty_by_id),
                "University of Geneva",
            )
            programmes.append(
                DiscoveredProgramme(
                    id=f"geneva-master-{record_id}",
                    name=name,
                    degree_type="Master",
                    faculty=faculty,
                    department=faculty,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "The official degree catalogue identifies this master's "
                        "programme. Geneva's enrollment conditions vary by applicant "
                        "profile and programme, and no universally applicable exact "
                        "opening-and-closing pair was found, so no dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-degree-catalogue-json-api",
                    evidence_quality="official-full-text",
                )
            )

        programmes.sort(key=lambda item: item.id)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "Geneva's official catalogue API contained "
                f"{len(programmes)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)
