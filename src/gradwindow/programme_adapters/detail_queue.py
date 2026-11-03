"""Shared, bounded detail scheduling. State is committed by discovery, never here.

Catalogue checkpoints contain metadata only. Reusing a checkpoint or a previous
detail must never count as a fresh observation of an application window.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from ..http_client import FetchFailure
from .base import DiscoveredCatalog, DiscoveredProgramme

T = TypeVar("T")


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _date(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class CatalogueCheckpoint:
    """Reuse only a completed, versioned directory; never stale-on-error dates."""

    def __init__(self, previous: dict, *, key: str, max_age_days: int = 7):
        self.previous = previous if isinstance(previous, dict) else {}
        self.key = key
        self.max_age_days = max(0, max_age_days)
        self.state: dict = {}
        self.reused = False

    def load(self, loader: Callable[[], DiscoveredCatalog]) -> DiscoveredCatalog:
        now = datetime.now(timezone.utc)
        fetched = _date(self.previous.get("fetchedAt"))
        payload = self.previous.get("catalogue")
        if (
            self.previous.get("key") == self.key
            and fetched is not None
            and timedelta(0) <= now - fetched < timedelta(days=self.max_age_days)
            and isinstance(payload, dict)
            and self.previous.get("hash") == fingerprint(payload)
        ):
            try:
                catalog = DiscoveredCatalog(
                    None,
                    [DiscoveredProgramme(**p) for p in deepcopy(payload["programmes"])],
                    warnings=deepcopy(payload["warnings"]),
                    diagnostics=deepcopy(payload["diagnostics"]),
                )
                self._validate(catalog)
            except (KeyError, TypeError, ValueError):
                pass
            else:
                self.reused = True
                self.state = deepcopy(self.previous)
                return catalog
        catalog = loader()
        self._validate(catalog)
        payload = {
            "programmes": [asdict(p) for p in catalog.programmes],
            "warnings": deepcopy(catalog.warnings),
            "diagnostics": deepcopy(catalog.diagnostics),
        }
        self.state = {
            "key": self.key,
            "fetchedAt": now.isoformat(),
            "hash": fingerprint(payload),
            "catalogue": payload,
        }
        return catalog

    @staticmethod
    def _validate(catalog: DiscoveredCatalog) -> None:
        ids = [p.id for p in catalog.programmes]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Catalogue checkpoint requires unique programme IDs")
        if catalog.application_opens_at or any(p.windows for p in catalog.programmes):
            raise ValueError(
                "Catalogue checkpoint must not contain application windows"
            )

    def attach(self, catalog: DiscoveredCatalog) -> None:
        catalog.adapter_state["catalogueCheckpoint"] = self.state
        catalog.diagnostics["catalogueCheckpoint"] = {
            "reused": self.reused,
            "fetchedAt": self.state["fetchedAt"],
            "maxAgeDays": self.max_age_days,
        }


class DetailQueue:
    """URL/option tasks rotate across runs, including failed and new tasks.

    A changed identity/intake/source revision invalidates a task's checkpoint.
    Entries record attempts separately from successful checks. Deferred tasks
    never acquire new evidence timestamps, and dry runs never persist this state.
    """

    def __init__(
        self,
        tasks: dict[str, object],
        previous: dict,
        *,
        budget: int,
        refresh_days: int = 1,
        now: datetime | None = None,
        legacy_attempts: dict[str, str] | None = None,
    ):
        self.now = now or datetime.now(timezone.utc)
        self.refresh_days = max(0, refresh_days)
        previous = previous if isinstance(previous, dict) else {}
        self.state = {}
        for url, identity in tasks.items():
            signature = fingerprint(identity)
            old = previous.get(url, {})
            self.state[url] = (
                dict(old)
                if isinstance(old, dict) and old.get("fingerprint") == signature
                else {"fingerprint": signature}
            )
            if legacy_attempts and "attemptedAt" not in self.state[url]:
                self.state[url]["attemptedAt"] = legacy_attempts.get(url, "")
        due = [
            url
            for url, entry in self.state.items()
            if (_date(entry.get("nextAttemptAt")) or self.now) <= self.now
        ]
        self.selected = sorted(
            due, key=lambda url: (self.state[url].get("attemptedAt", ""), url)
        )[: max(0, budget)]
        self.attempted: set[str] = set()
        self.checked: set[str] = set()
        self.failed: set[str] = set()

    def record(self, url: str, status: str, *, checked: bool) -> None:
        entry = self.state[url]
        self.attempted.add(url)
        entry.pop("error", None)
        entry.update(attemptedAt=self.now.isoformat(), status=status)
        if checked:
            self.checked.add(url)
            entry.update(checkedAt=self.now.isoformat(), failures=0)
            delay = timedelta(days=self.refresh_days)
        else:
            self.failed.add(url)
            failures = min(int(entry.get("failures", 0)) + 1, 8)
            entry["failures"] = failures
            delay = timedelta(hours=min(2**failures, 48))
        entry["nextAttemptAt"] = (self.now + delay).isoformat()

    def record_error(self, url: str, error: Exception) -> bool:
        transport = isinstance(error, FetchFailure)
        diagnostics = getattr(error, "transport_diagnostics", {})
        status = (
            "budget-exhausted"
            if diagnostics.get("fallbackBudgetExhausted", 0)
            else error.kind
            if transport
            else "needs-page-review"
        )
        self.record(url, status, checked=False)
        self.state[url]["error"] = str(error)[:500]
        # Pause this host after a transport failure, but isolate parser failures.
        return transport

    def run(
        self,
        inspect: Callable[[str], T],
        *,
        interval_seconds: float = 0,
        jitter_seconds: float = 0,
    ) -> tuple[dict[str, T], dict[str, Exception]]:
        results, errors = {}, {}
        for index, url in enumerate(self.selected):
            if index and interval_seconds > 0:
                time.sleep(interval_seconds + random.uniform(0, max(0, jitter_seconds)))
            try:
                results[url] = inspect(url)
            except (FetchFailure, ValueError) as exc:
                errors[url] = exc
                if self.record_error(url, exc):
                    break
            else:
                self.record(url, "checked", checked=True)
        return results, errors

    def attach(self, catalog: DiscoveredCatalog) -> None:
        for programme in catalog.programmes:
            if programme.source_url not in self.checked:
                programme.windows = []
                programme.evidence_document_hash = None
                if programme.parse_status != "needs-review":
                    programme.parse_status = (
                        "needs-review"
                        if programme.source_url in self.failed
                        else "catalogue-only"
                    )
        catalog.adapter_state["detailQueue"] = self.state
        catalog.diagnostics["detailQueue"] = {
            "eligibleTasks": len(self.state),
            "attemptedThisRun": len(self.attempted),
            "checkedThisRun": len(self.checked),
            "failedThisRun": len(self.failed),
            "deferredThisRun": len(self.state) - len(self.attempted),
            "neverChecked": sum(not e.get("checkedAt") for e in self.state.values()),
            "lastOutcomeCounts": {
                status: sum(
                    e.get("status", "unvisited") == status for e in self.state.values()
                )
                for status in sorted(
                    {e.get("status", "unvisited") for e in self.state.values()}
                )
            },
        }
        catalog.diagnostics.update(
            detailSucceededProgrammeIds=sorted(
                p.id for p in catalog.programmes if p.source_url in self.checked
            ),
            detailFailedProgrammeIds=sorted(
                p.id for p in catalog.programmes if p.source_url in self.failed
            ),
            detailUnvisitedProgrammeIds=sorted(
                p.id for p in catalog.programmes if p.source_url not in self.attempted
            ),
        )
