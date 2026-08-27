from __future__ import annotations

import concurrent.futures
import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .content import evidence_matches_target_dates
from .evidence_store import evidence_snapshot_exists, write_evidence_snapshots
from .io import read_json, write_json
from .monitor import check_university, summarize_monitor_results
from .paths import (
    APPLICATION_SOURCE_STATE_PATH,
    APPLICATIONS_PATH,
    EVIDENCE_DIR,
)

DEFAULT_MAX_SOURCE_URLS = 400


def monitor_application_sources(
    applications_path: Path = APPLICATIONS_PATH,
    state_path: Path = APPLICATION_SOURCE_STATE_PATH,
    evidence_dir: Path | None = None,
    workers: int = 8,
    max_urls: int | None = DEFAULT_MAX_SOURCE_URLS,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    if evidence_dir is None:
        evidence_dir = (
            EVIDENCE_DIR
            if applications_path == APPLICATIONS_PATH
            else state_path.parent / "evidence"
        )
    applications = read_json(applications_path)["applications"]
    old_state = read_json(state_path, {"applications": {}})
    old_entries = old_state.get("applications", {})
    records_by_url: dict[str, list[dict]] = {}
    for record in applications:
        records_by_url.setdefault(record["sourceUrl"], []).append(record)

    previous_by_url = {
        url: _previous_result(records, old_entries)
        for url, records in records_by_url.items()
    }
    ordered_urls = sorted(
        records_by_url,
        key=lambda url: (
            bool((previous_by_url[url] or {}).get("checkedAt")),
            (previous_by_url[url] or {}).get("checkedAt", ""),
            url,
        ),
    )
    selected_urls = set(
        ordered_urls if max_urls is None else ordered_urls[: max(0, max_urls)]
    )
    deferred_at = datetime.now(timezone.utc).isoformat()

    results_by_url: dict[str, dict] = {
        url: _deferred_result(url, previous_by_url[url], deferred_at)
        for url in records_by_url
        if url not in selected_urls
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {}
        for url in ordered_urls:
            if url not in selected_urls:
                continue
            records = records_by_url[url]
            previous = previous_by_url[url]
            future = executor.submit(
                check_university,
                {
                    "homepageUrl": url,
                    "evidenceDates": sorted(
                        {
                            value
                            for record in records
                            for value in (
                                record.get("opensAt"),
                                record.get("closesAt"),
                            )
                            if value
                        }
                    ),
                },
                previous,
                True,
            )
            future_map[future] = url
        completed = 0
        for future in concurrent.futures.as_completed(future_map):
            url = future_map[future]
            try:
                results_by_url[url] = future.result()
            except Exception as exc:
                results_by_url[url] = {
                    "url": url,
                    "checkedAt": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "message": str(exc)[:240],
                    "changed": False,
                }
            results_by_url[url]["runStatus"] = "checked"
            results_by_url[url].pop("deferredAt", None)
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, len(selected_urls))

    entries = {}
    evidence_snapshots = []
    for record in applications:
        result = dict(results_by_url[record["sourceUrl"]])
        context = result.pop(
            "evidenceContext",
            {
                "excerpt": result.pop("evidenceExcerpt", ""),
                "contentSelector": "main|article|[role=main]|body",
                "matchedTextBefore": "",
                "matchedText": "",
                "matchedTextAfter": "",
            },
        )
        excerpt = context["excerpt"]
        result["recordId"] = record["id"]
        result["universityId"] = record["universityId"]
        entries[record["id"]] = result
        if result.get("runStatus") == "checked" and result["status"] == "ok":
            target_dates = [value for value in _evidence_target_dates(record) if value]
            if target_dates and not evidence_matches_target_dates(
                excerpt,
                target_dates,
            ):
                context_excerpt = "\n".join(
                    value
                    for value in (
                        context["matchedTextBefore"],
                        context["matchedText"],
                        context["matchedTextAfter"],
                    )
                    if value
                )
                if evidence_matches_target_dates(context_excerpt, target_dates):
                    excerpt = context_excerpt
                    context["excerpt"] = context_excerpt
                elif evidence_snapshot_exists(
                    evidence_dir,
                    record["universityId"],
                    record["id"],
                ):
                    continue
                else:
                    excerpt = ""
            evidence_snapshots.append(
                {
                    "recordId": record["id"],
                    "universityId": record["universityId"],
                    "sourceUrl": record["sourceUrl"],
                    "finalUrl": result["url"],
                    "capturedAt": result["checkedAt"],
                    "contentHash": result.get("contentHash"),
                    "contentType": result.get("contentType"),
                    "bytesRead": result.get("bytesRead"),
                    "truncated": result.get("truncated", False),
                    "excerpt": excerpt,
                    "excerptHash": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                    "contentSelector": context["contentSelector"],
                    "matchedTextBefore": context["matchedTextBefore"],
                    "matchedText": context["matchedText"],
                    "matchedTextAfter": context["matchedTextAfter"],
                }
            )

    summary = summarize_monitor_results(entries)
    summary["checked"] = sum(
        item.get("runStatus") == "checked" for item in entries.values()
    )
    summary["deferred"] = sum(
        item.get("runStatus") == "deferred" for item in entries.values()
    )
    write_evidence_snapshots(evidence_dir, evidence_snapshots)
    write_json(
        state_path,
        {
            "meta": {
                "checkedAt": datetime.now(timezone.utc).isoformat(),
                "uniqueSourcePages": len(records_by_url),
                "uniqueSourcePagesChecked": len(selected_urls),
                "uniqueSourcePagesDeferred": len(records_by_url) - len(selected_urls),
                "runStatus": (
                    "complete"
                    if len(selected_urls) == len(records_by_url)
                    else "partial"
                ),
                "summary": summary,
            },
            "applications": entries,
        },
    )
    return summary


def _previous_result(records: list[dict], old_entries: dict[str, dict]) -> dict | None:
    previous = [
        old_entries[record["id"]] for record in records if record["id"] in old_entries
    ]
    return max(previous, key=lambda item: item.get("checkedAt", ""), default=None)


def _deferred_result(url: str, previous: dict | None, deferred_at: str) -> dict:
    if previous is None:
        return {
            "url": url,
            "status": "deferred",
            "changed": False,
            "firstSeenAt": deferred_at,
            "runStatus": "deferred",
            "deferredAt": deferred_at,
            "message": "Deferred by the bounded source-monitor rotation.",
        }
    return {
        **previous,
        "runStatus": "deferred",
        "deferredAt": deferred_at,
    }


def _evidence_target_dates(record: dict) -> tuple[str | None, ...]:
    if "configured cycle-default opening date" in record.get("evidence", ""):
        return (record.get("closesAt"),)
    return (record.get("opensAt"), record.get("closesAt"))
