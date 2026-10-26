from __future__ import annotations

import pytest

from gradwindow.io import read_json, write_json
from gradwindow.programme_adapters.generic import (
    GenericProgrammeAdapter,
    GenericProgrammeConfig,
)
from gradwindow.programme_discovery import discover_programmes

SEED_URL = "https://example.edu/graduate/programmes"
DETAIL_URLS = [f"https://example.edu/graduate/msc-{name}" for name in "abc"]
CATALOGUE = "".join(
    f'<a href="{url}">MSc {name.upper()}</a>'
    for name, url in zip("abc", DETAIL_URLS, strict=True)
)


def _adapter(*, budget=2, intake="Fall 2027"):
    return GenericProgrammeAdapter(
        GenericProgrammeConfig(
            university_id="example-university",
            school_prefix="example",
            seed_urls=(SEED_URL,),
            official_domains=("example.edu",),
            default_application_url="https://example.edu/apply",
            default_intake=intake,
            max_detail_pages=budget,
        )
    )


def _discovery(tmp_path, adapter, fetcher):
    programs = tmp_path / "programs.json"
    if not programs.exists():
        write_json(programs, {"programs": []})
    return discover_programmes(
        adapter,
        programs_path=programs,
        applications_path=tmp_path / "applications.json",
        candidates_path=tmp_path / "programme-candidates.json",
        state_path=tmp_path / "programme-catalog-state.json",
        fetcher=fetcher,
    )


def test_generic_details_rotate_across_discovery_runs_and_keep_full_catalogue(tmp_path):
    visited = []

    def fetcher(url):
        if url == SEED_URL:
            return CATALOGUE
        visited.append(url)
        return f"<h1>MSc {url[-1].upper()}</h1><p>Dates to be confirmed.</p>"

    _discovery(tmp_path, _adapter(), fetcher)
    state = read_json(tmp_path / "programme-catalog-state.json")["universities"][
        "example-university"
    ]
    assert len(state["programmes"]) == 3
    assert set(visited) == set(DETAIL_URLS[:2])
    assert state["adapterDiagnostics"]["detailUnvisitedProgrammeIds"] == [
        "example-msc-c"
    ]

    visited.clear()
    _discovery(tmp_path, _adapter(), fetcher)
    assert DETAIL_URLS[2] in visited
    assert len(visited) == 2
    candidates = read_json(tmp_path / "programme-candidates.json")["items"]
    assert len(candidates) == 3


def test_generic_detail_failure_is_retained_and_does_not_starve_unvisited_pages(
    tmp_path,
):
    visited = []

    def fetcher(url):
        if url == SEED_URL:
            return CATALOGUE
        visited.append(url)
        if url == DETAIL_URLS[0]:
            raise RuntimeError("temporarily unavailable")
        return f"<h1>MSc {url[-1].upper()}</h1>"

    _discovery(tmp_path, _adapter(budget=1), fetcher)
    state = read_json(tmp_path / "programme-catalog-state.json")["universities"][
        "example-university"
    ]
    assert len(state["programmes"]) == 3
    assert state["adapterDiagnostics"]["detailFailedProgrammeIds"] == ["example-msc-a"]
    assert state["adapterDiagnostics"]["detailMonitor"]["failedThisRun"] == 1
    assert state["adapterWarnings"][0]["reason"] == "detail-fetch-failed"

    visited.clear()
    _discovery(tmp_path, _adapter(budget=1), fetcher)
    assert visited == [DETAIL_URLS[1]]


def test_generic_deferred_details_do_not_recycle_dates_or_default_deadlines():
    adapter = _adapter(budget=1)

    def fetcher(url):
        if url == SEED_URL:
            return CATALOGUE
        return (
            f"<h1>MSc {url[-1].upper()}</h1><p>Application portal opens September 1, 2026. "
            "Application deadline January 14, 2027.</p>"
        )

    first = adapter.parse_catalog_from_fetcher(fetcher)
    assert first.programmes[0].windows
    second_adapter = _adapter(budget=1)
    second_adapter.prepare_discovery({"adapterState": first.adapter_state})
    second = second_adapter.parse_catalog_from_fetcher(fetcher)
    deferred = next(item for item in second.programmes if item.id == "example-msc-a")
    assert deferred.windows == []
    assert deferred.parse_status == "catalogue-only"
    assert deferred.evidence_quality == "catalogue-only"


def test_generic_new_cycle_resets_detail_rotation():
    adapter = _adapter(budget=1)

    def fetcher(url):
        return CATALOGUE if url == SEED_URL else "<h1>MSc A</h1>"

    first = adapter.parse_catalog_from_fetcher(fetcher)
    next_cycle = _adapter(budget=1, intake="Fall 2028")
    next_cycle.prepare_discovery({"adapterState": first.adapter_state})
    result = next_cycle.parse_catalog_from_fetcher(fetcher)
    assert result.diagnostics["detailSucceededProgrammeIds"] == ["example-msc-a"]
    assert result.diagnostics["detailMonitor"]["unvisitedPages"] == 2


@pytest.mark.parametrize("failed", [False, True])
def test_unchecked_detail_preserves_previous_candidate_without_reverification(
    tmp_path, failed
):
    def exact_fetcher(url):
        if url == SEED_URL:
            return CATALOGUE
        return (
            f"<h1>MSc {url[-1].upper()}</h1><p>Application portal opens September 1, 2026. "
            "Application deadline January 14, 2027.</p>"
        )

    _discovery(tmp_path, _adapter(budget=3), exact_fetcher)
    path = tmp_path / "programme-candidates.json"
    original = read_json(path)["items"]

    def failure_fetcher(url):
        if url == SEED_URL:
            return CATALOGUE
        raise RuntimeError("unavailable")

    _discovery(tmp_path, _adapter(budget=3 if failed else 0), failure_fetcher)
    assert read_json(path)["items"] == original
    state = read_json(tmp_path / "programme-catalog-state.json")["universities"][
        "example-university"
    ]
    assert state["windows"] == {}


def test_successful_recheck_can_clear_previously_observed_dates(tmp_path):
    def exact_fetcher(url):
        if url == SEED_URL:
            return CATALOGUE
        return (
            f"<h1>MSc {url[-1].upper()}</h1><p>Application portal opens September 1, 2026. "
            "Application deadline January 14, 2027.</p>"
        )

    _discovery(tmp_path, _adapter(budget=3), exact_fetcher)
    _discovery(
        tmp_path,
        _adapter(budget=3),
        lambda url: (
            CATALOGUE
            if url == SEED_URL
            else f"<h1>MSc {url[-1].upper()}</h1><p>Dates to be confirmed.</p>"
        ),
    )
    assert all(
        not item["windows"]
        for item in read_json(tmp_path / "programme-candidates.json")["items"]
    )
