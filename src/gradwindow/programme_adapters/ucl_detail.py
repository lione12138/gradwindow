"""Bounded monitoring of UCL's current course application-date sections.

This monitor records evidence for review, never generates application windows.
Course-option sections are isolated before reading any application evidence.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from ..http_client import FetchFailure
from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise
from .ucl import CATALOG_URL, programme_name_key


def inspect_detail(html: str, programme: DiscoveredProgramme) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h1.course-hero__title")
    option = parse_qs(urlparse(programme.source_url).query).get("option", [])
    scope = None
    if heading and heading.select("[data-course-option]"):
        matches = [
            node
            for node in heading.select("[data-course-option]")
            if programme_name_key(node.get_text(" ", strip=True))
            == programme_name_key(programme.name)
            and (not option or option == [node.get("data-course-option")])
        ]
        if len(matches) != 1:
            raise ValueError(
                "UCL detail course option identity is ambiguous or missing"
            )
        heading = matches[0]
        scope = heading["data-course-option"]
    elif option:
        raise ValueError("UCL detail option scope is missing")
    if not heading or programme_name_key(heading.get_text(" ", strip=True)) != (
        programme_name_key(programme.name)
    ):
        raise ValueError("UCL detail course identity does not match the catalogue")

    def section(selector):
        root = soup.select_one(selector)
        if root is None:
            raise ValueError("UCL detail application-date sections are missing")
        if scope:
            matches = root.find_all(attrs={"data-course-option": scope})
            if len(matches) != 1:
                raise ValueError(
                    "UCL detail section option scope is missing or ambiguous"
                )
            return matches[0]
        if root.select("[data-course-option]"):
            raise ValueError("UCL detail section has an unidentified option scope")
        return root

    fields: dict[str, list[str]] = {}
    for item in section("#key-information").select(".key-info-item"):
        label = item.select_one(".key-info-item__label")
        value = item.select_one(".key-info-item__value")
        if label and value:
            fields.setdefault(normalise(label.get_text(" ", strip=True)), []).append(
                normalise(value.get_text(" ", strip=True))
            )
    starts = fields.get("Course starts", [])
    if not starts or set(starts) != set(programme.available_intakes):
        raise ValueError("UCL detail intake does not match the catalogue")
    deadlines = fields.get("Application deadlines", [])
    apply_section = section("#apply")
    apply = apply_section.select_one(".apply-chooser")
    if option and deadlines and apply is None:
        text = normalise(apply_section.get_text(" ", strip=True))
        links = apply_section.select("a[href]")
        if len(links) == 1:
            parent = urljoin(programme.source_url, links[0]["href"])
            parsed = urlparse(parent)
            expected = urlparse(programme.source_url)
            if (
                parsed.scheme == expected.scheme == "https"
                and parsed.netloc == expected.netloc == "www.ucl.ac.uk"
                and parsed.path == expected.path
                and not parsed.query
                and parsed.fragment == "apply"
                and text.startswith("Apply for ")
                and " to access this study option." in text
            ):
                return {
                    "status": "apply-via-parent",
                    "parentApplicationUrl": parent,
                    "deadlineText": " | ".join(deadlines),
                    "applicationText": text,
                    "evidenceHash": hashlib.sha256(
                        "\n".join(
                            [programme.name, scope, *starts, *deadlines, text, parent]
                        ).encode()
                    ).hexdigest(),
                }
    if not deadlines or not apply:
        raise ValueError("UCL detail application-date sections are missing")
    apply_text = normalise(apply.get_text(" ", strip=True))
    messages = [
        normalise(node.get_text(" ", strip=True))
        for node in apply.select(".apply-chooser__slot-message")
    ]
    pending = (
        set(deadlines) == {"To be confirmed."}
        and messages == ["The course application dates are to be confirmed."]
        and not apply.select("form, time")
    )
    evidence = "\n".join([programme.name, *starts, *deadlines, apply_text])
    return {
        "status": "dates-to-be-confirmed" if pending else "needs-date-review",
        "deadlineText": " | ".join(deadlines),
        "applicationText": apply_text,
        "evidenceHash": hashlib.sha256(evidence.encode()).hexdigest(),
    }


def monitor_details(
    catalog: DiscoveredCatalog,
    fetcher: Fetcher,
    previous: dict,
    *,
    budget: int,
) -> None:
    eligible = {
        p.source_url: p for p in catalog.programmes if p.source_url != CATALOG_URL
    }
    # A previous cycle or changed programme identity must never supply current evidence.
    state = {
        url: dict(previous[url])
        for url, p in eligible.items()
        if isinstance(previous.get(url), dict)
        and previous[url].get("intakes") == p.available_intakes
        and previous[url].get("programmeId") == p.id
    }
    order = sorted(
        eligible, key=lambda url: (state.get(url, {}).get("attemptedAt", ""), url)
    )
    attempted = 0
    for url in order[: max(0, budget)]:
        p = eligible[url]
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "programmeId": p.id,
            "intakes": p.available_intakes,
            "attemptedAt": now,
        }
        attempted += 1
        try:
            result = inspect_detail(fetcher(url), p)
        except (FetchFailure, ValueError) as exc:
            entry.update(
                status="fetch-failed"
                if isinstance(exc, FetchFailure)
                else "needs-page-review"
            )
            entry["error"] = str(exc)[:500]
            catalog.warnings.append({"sourceUrl": url, "reason": entry["status"]})
            state[url] = entry
            # Stop after transport failure: do not consume the remaining fallback
            # allowance against a blocked/rate-limited upstream.
            if isinstance(exc, FetchFailure):
                break
        else:
            entry.update(result, checkedAt=now)
            state[url] = entry
            if result["status"] == "needs-date-review":
                catalog.warnings.append(
                    {"sourceUrl": url, "reason": "needs-date-review"}
                )
    catalog.adapter_state["detailMonitor"] = state
    catalog.diagnostics["detailWindowDiscovery"] = "bounded-monitor-only"
    catalog.diagnostics["detailMonitor"] = {
        "eligiblePages": len(eligible),
        "eligibleOptionRoutes": sum(
            bool(urlparse(p.source_url).query) for p in catalog.programmes
        ),
        "attemptedThisRun": attempted,
        "unvisitedPages": len(eligible) - len(state),
        "lastObservedStatusCounts": {
            status: sum(entry.get("status") == status for entry in state.values())
            for status in (
                "dates-to-be-confirmed",
                "needs-date-review",
                "needs-page-review",
                "fetch-failed",
                "apply-via-parent",
            )
        },
    }
