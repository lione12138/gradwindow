from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.aalto.fi/aalto_api/studies/list"
APPLICATION_URL = "https://www.aalto.fi/en/study-at-aalto/apply-to-masters-programmes"


class AaltoAdapter(OfficialCatalogAdapter):
    university_id = "aalto-university"
    school_prefix = "aalto"
    institution_name = "Aalto University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 80
    retrieval_method = "official-json-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, document: str) -> DiscoveredCatalog:
        payload = json.loads(document)
        study_options = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(study_options, list):
            raise ValueError("Aalto studies API did not return a data list")
        entries = self.extract_entries(document)
        catalog = self._catalog(entries)
        catalog.diagnostics = {
            "apiStudyOptions": len(study_options),
            "apiMasterOptions": len(entries),
        }
        return catalog

    def extract_entries(self, document: str) -> list[CatalogEntry]:
        payload = json.loads(document)
        study_options = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(study_options, list):
            raise ValueError("Aalto studies API did not return a data list")
        entries = []
        for study_option in study_options:
            if (
                not isinstance(study_option, dict)
                or study_option.get("degreeType") != "masters"
            ):
                continue
            source_url = str(study_option.get("url") or "").strip()
            path = urlparse(source_url).path
            if "/en/study-options/" not in path:
                continue
            name_slug = path.rstrip("/").split("/")[-1]
            if "master" not in name_slug or "bachelor" in name_slug:
                continue
            if "master-of-arts" in name_slug:
                degree = "MA"
            elif "master-of-science" in name_slug:
                degree = "MSc"
            else:
                degree = "Master"
            name = (
                re.sub(
                    r"-(?:master-of-(?:science|arts)(?:-[a-z-]+)?|masters?-programme.*|master.*)$",
                    "",
                    name_slug,
                )
                .replace("-", " ")
                .title()
            )
            entries.append(
                entry(
                    name=name,
                    degree_type=degree,
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
