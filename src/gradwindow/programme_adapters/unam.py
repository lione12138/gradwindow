from __future__ import annotations

import json

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = (
    "https://plataformatransparencia.unam.mx:8443/unam-tpa-api/consulta/"
    "A74F01/485/7223/2026?cmd=get-records&limit=1000&offset=0&selected=0"
)
APPLICATION_URL = "https://posgrado.dgae.unam.mx/ingreso/"


class UNAMAdapter(OfficialCatalogAdapter):
    university_id = "universidad-nacional-aut-noma-de-m-xico-unam"
    school_prefix = "unam"
    institution_name = "Universidad Nacional Autónoma de México"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 50
    retrieval_method = "official-2026-transparency-api"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        payload = json.loads(html)
        if payload.get("status") != "success":
            raise ValueError("UNAM transparency API did not return success")
        entries: list[CatalogEntry] = []
        for record in payload.get("records", []):
            degree = str(record.get("7230", "")).strip()
            name = str(record.get("7227", "")).strip()
            if not degree.casefold().startswith("maestr") or not name:
                continue
            source_url = str(record.get("7233") or record.get("7234") or CATALOG_URL)
            entries.append(
                entry(
                    name=name,
                    degree_type="Maestría",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
