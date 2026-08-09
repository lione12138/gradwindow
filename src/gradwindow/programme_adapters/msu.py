from __future__ import annotations

import json
import math
import re
from urllib.parse import urlencode

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://openday.msu.ru/programs"
APPLICATION_URL = "https://cpk.msu.ru/"
STORE_ENDPOINT = "https://store.tildacdn.com/api/getproductslist/"


class MSUAdapter:
    university_id = "lomonosov-moscow-state-university"
    school_prefix = "msu"
    institution_name = "Lomonosov Moscow State University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-tilda-programme-catalogue-api"

    def __init__(
        self,
        minimum_expected_programmes: int = 200,
        page_size: int = 100,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.page_size = page_size

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        page = fetcher(CATALOG_URL)
        recid = _option(page, "recid")
        storepart = _option(page, "storepart")
        products: list[dict] = []
        total = 1
        slice_number = 1
        while slice_number <= math.ceil(total / self.page_size):
            query = urlencode(
                {
                    "storepartuid": storepart,
                    "recid": recid,
                    "getparts": "true",
                    "getoptions": "true",
                    "flag_root": "withroot",
                    "size": self.page_size,
                    "slice": slice_number,
                }
            )
            payload = json.loads(fetcher(f"{STORE_ENDPOINT}?{query}"))
            if not isinstance(payload, dict) or not isinstance(
                payload.get("products"), list
            ):
                raise ValueError("MSU catalogue API returned an invalid payload")
            total = int(payload.get("total", 0))
            products.extend(payload["products"])
            slice_number += 1

        programmes: dict[str, DiscoveredProgramme] = {}
        for product in products:
            characteristics = {
                normalise(item.get("title", "")): normalise(item.get("value", ""))
                for item in product.get("characteristics", [])
                if isinstance(item, dict)
            }
            level = " ".join(characteristics.values()).casefold()
            if "магистратура" not in level and "master" not in level:
                continue
            name = normalise(product.get("title", ""))
            source_url = str(product.get("url", "")).strip()
            uid = str(product.get("uid", "")).strip()
            if not name or not source_url or not uid:
                continue
            faculty = next(
                (
                    value
                    for key, value in characteristics.items()
                    if key.casefold() in {"факультет", "faculty"}
                ),
                self.institution_name,
            )
            programme_id = f"msu-{slug(name)}-{slug(uid)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in MSU's official programme catalogue API. "
                    "No official pair of exact opening and closing dates was "
                    "published, so no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: (item.name, item.id))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"MSU catalogue contained {len(result)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _option(html: str, name: str) -> str:
    match = re.search(rf"{name}\s*:\s*['\"]([^'\"]+)['\"]", html)
    if match is None:
        raise ValueError(f"MSU catalogue did not expose Tilda {name}")
    return match.group(1)
