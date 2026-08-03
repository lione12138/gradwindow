from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://webtools.au.dk/api/masters/getlist?lang=en"
APPLICATION_URL = "https://masters.au.dk/how-to-apply"


class AarhusAdapter(OfficialCatalogAdapter):
    university_id = "aarhus-university"
    school_prefix = "aarhus"
    institution_name = "Aarhus University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (
        "https://masters.au.dk/deadlines-and-important-dates",
        APPLICATION_URL,
    )
    minimum_expected_programmes = 90
    retrieval_method = "official-programme-api"

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = self._rows(payload)
        names_by_id = {row["ID"]: row["Name"].strip() for row in rows}
        entries = []
        for row in rows:
            name = row["Name"].strip()
            source_url = str(row.get("Uri") or "").strip()
            if not name or not source_url:
                continue
            parent_id = row.get("Parent") or 0
            if parent_id and names_by_id.get(parent_id):
                name = f"{names_by_id[parent_id]}: {name}"
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url.replace(
                        "http://masters.au.dk", "https://masters.au.dk"
                    ),
                    base_url=CATALOG_URL,
                )
            )
        return entries

    @staticmethod
    def _rows(payload: str) -> list[dict[str, object]]:
        if payload.lstrip().startswith("{"):
            return json.loads(payload)["Items"]

        root = ET.fromstring(payload)
        items = next(
            (node for node in root if node.tag.rsplit("}", 1)[-1] == "Items"),
            None,
        )
        if items is None:
            return []

        rows: list[dict[str, object]] = []
        for item in items:
            row = {
                child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
                for child in item
                if len(child) == 0
            }
            row["ID"] = int(str(row.get("ID") or 0))
            row["Parent"] = int(str(row.get("Parent") or 0))
            rows.append(row)
        return rows
