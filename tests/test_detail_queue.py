from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from test_ucl_detail import programme

from gradwindow.http_client import FetchFailure
from gradwindow.programme_adapters.base import DiscoveredCatalog, DiscoveredWindow
from gradwindow.programme_adapters.detail_queue import CatalogueCheckpoint, DetailQueue

NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


def test_queue_bounds_cold_start_resumes_and_schedules_rechecks():
    tasks = {str(i): [f"programme-{i}", "September 2027"] for i in range(5)}
    first = DetailQueue(tasks, {}, budget=2, now=NOW)
    results, _ = first.run(lambda url: url)
    assert list(results) == ["0", "1"]
    second = DetailQueue(tasks, first.state, budget=2, now=NOW)
    assert second.selected == ["2", "3"]
    second.run(lambda url: url)
    third = DetailQueue(tasks, second.state, budget=2, now=NOW)
    assert third.selected == ["4"]
    third.run(lambda url: url)
    assert DetailQueue(tasks, third.state, budget=2, now=NOW).selected == []
    assert DetailQueue(
        tasks, third.state, budget=2, now=NOW + timedelta(days=1)
    ).selected == ["0", "1"]


def test_changed_identity_or_intake_requeues_without_old_evidence():
    old = DetailQueue({"url": ["p", "2027"]}, {}, budget=1, now=NOW)
    old.run(lambda _: "ok")
    new = DetailQueue({"url": ["p", "2028"]}, old.state, budget=1, now=NOW)
    assert new.selected == ["url"]
    assert "checkedAt" not in new.state["url"]
    assert DetailQueue({}, old.state, budget=1, now=NOW).state == {}


def test_parser_failure_isolated_transport_pauses_and_backoff_survives_restart():
    queue = DetailQueue({key: key for key in "abcd"}, {}, budget=4, now=NOW)

    def inspect(key):
        if key == "a":
            raise ValueError("changed markup")
        if key == "c":
            raise FetchFailure("slow down", kind="rate-limited", status_code=429)
        return key

    results, errors = queue.run(inspect)
    assert results == {"b": "b"}
    assert set(errors) == {"a", "c"}
    assert queue.state["a"]["status"] == "needs-page-review"
    assert queue.state["c"]["status"] == "rate-limited"
    assert "attemptedAt" not in queue.state["d"]
    assert DetailQueue(
        {key: key for key in "abcd"}, queue.state, budget=4, now=NOW
    ).selected == ["d"]
    retry = DetailQueue({"a": "a"}, queue.state, budget=1, now=NOW + timedelta(hours=2))
    retry.run(lambda _: "recovered")
    assert retry.state["a"]["failures"] == 0
    assert "error" not in retry.state["a"]


def test_budget_exhaustion_distinguished_from_upstream_block():
    queue = DetailQueue({"url": "p"}, {}, budget=1, now=NOW)
    error = FetchFailure("blocked", kind="blocked", status_code=403)
    error.transport_diagnostics = {"fallbackBudgetExhausted": 1}
    assert queue.record_error("url", error)
    assert queue.state["url"]["status"] == "budget-exhausted"
    assert "checkedAt" not in queue.state["url"]


def test_unexpected_programming_error_is_not_hidden_as_a_monitor_result():
    queue = DetailQueue({"url": "p"}, {}, budget=1)
    with pytest.raises(TypeError):
        queue.run(lambda _: 1 + "wrong")


def test_checkpoint_reuse_does_not_refresh_timestamp_or_share_mutable_records():
    cache = CatalogueCheckpoint({}, key="school:v1")
    catalog = cache.load(lambda: DiscoveredCatalog(None, [programme()]))
    catalog.programmes[0].available_intakes.append("changed later")
    original = deepcopy(cache.state)
    second = CatalogueCheckpoint(cache.state, key="school:v1")
    restored = second.load(lambda: pytest.fail("fresh catalogue should not refetch"))
    restored.programmes[0].available_intakes.append("also changed")
    assert cache.state == original == second.state
    assert second.reused


@pytest.mark.parametrize("reason", ["expired", "force", "version", "corrupt", "future"])
def test_invalid_checkpoint_refetches_and_failed_refresh_does_not_save(reason):
    cache = CatalogueCheckpoint({}, key="v1")
    cache.load(lambda: DiscoveredCatalog(None, [programme()]))
    if reason == "expired":
        cache.state["fetchedAt"] = "2000-01-01T00:00:00+00:00"
    elif reason == "future":
        cache.state["fetchedAt"] = "2099-01-01T00:00:00+00:00"
    elif reason == "corrupt":
        cache.state["catalogue"]["programmes"].clear()
    current = CatalogueCheckpoint(
        cache.state,
        key="v2" if reason == "version" else "v1",
        max_age_days=0 if reason == "force" else 7,
    )

    def failed():
        raise ValueError("incomplete directory")

    with pytest.raises(ValueError, match="incomplete directory"):
        current.load(failed)
    assert current.state == {}


def test_catalogue_checkpoint_rejects_dates_and_duplicate_identities():
    p = programme()
    cache = CatalogueCheckpoint({}, key="v1")
    with pytest.raises(ValueError, match="unique programme"):
        cache.load(lambda: DiscoveredCatalog(None, [p, p]))
    p.windows = [DiscoveredWindow("Main", "2027-01-01")]
    with pytest.raises(ValueError, match="must not contain"):
        cache.load(lambda: DiscoveredCatalog(None, [p]))


def test_deferred_cached_dates_cannot_create_new_candidates_or_refresh_evidence():
    p = programme()
    p.windows = [DiscoveredWindow("Main", "2027-01-01")]
    p.evidence_document_hash = "old-evidence"
    p.parse_status = "parsed"
    catalog = DiscoveredCatalog(None, [p])
    queue = DetailQueue({p.source_url: p.id}, {}, budget=0)
    queue.attach(catalog)
    assert p.windows == []
    assert p.evidence_document_hash is None
    assert p.parse_status == "catalogue-only"
    assert catalog.diagnostics["detailUnvisitedProgrammeIds"] == [p.id]
