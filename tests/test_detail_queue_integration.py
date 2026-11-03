"""The same scheduling contract against three different official-source formats."""

import pytest
from test_edinburgh_programme_adapter import CATALOGUE, EXACT, ROUNDS, STANDARD
from test_toronto_programme_adapter import _fetcher as toronto_fetch
from test_ucl_current import card, page
from test_ucl_detail import HTML

from gradwindow.http_client import FetchFailure
from gradwindow.io import read_json, write_json
from gradwindow.programme_adapters.edinburgh import CATALOG_URL as EDINBURGH_URL
from gradwindow.programme_adapters.edinburgh import EdinburghAdapter
from gradwindow.programme_adapters.toronto import PROGRAMS_API_URL, TorontoAdapter
from gradwindow.programme_adapters.ucl import CATALOG_URL as UCL_URL
from gradwindow.programme_adapters.ucl import UCLAdapter
from gradwindow.programme_discovery import discover_programmes


def school_case(school):
    if school == "ucl":
        directory = page(
            "".join(
                card(f"{name} MSc", route=f"{name.lower()}-msc")
                for name in ("Alpha", "Beta", "Gamma")
            )
        )

        def fetch(url):
            if url == UCL_URL:
                return directory
            name = url.rsplit("/", 1)[-1].split("-")[0].title()
            return HTML.replace("Advanced Materials Science", name)

        return lambda: UCLAdapter(3, 3, detail_refresh_budget=1), fetch, {UCL_URL}
    if school == "edinburgh":
        return (
            lambda: EdinburghAdapter(
                3, detail_refresh_budget=1, detail_interval_seconds=0
            ),
            lambda url: (
                CATALOGUE
                if url == EDINBURGH_URL
                else EXACT
                if "/129-" in url
                else STANDARD
                if "/98-" in url
                else ROUNDS
            ),
            {EDINBURGH_URL},
        )
    return (
        lambda: TorontoAdapter(4, detail_refresh_budget=1, detail_interval_seconds=0),
        toronto_fetch,
        {PROGRAMS_API_URL.format(page=1)},
    )


def paths_for(tmp_path):
    paths = {
        key: tmp_path / name
        for key, name in {
            "programs_path": "programs.json",
            "applications_path": "applications.json",
            "candidates_path": "programme-candidates.json",
            "window_candidates_path": "window-candidates.json",
            "state_path": "state.json",
        }.items()
    }
    write_json(paths["programs_path"], {"programs": []})
    write_json(paths["applications_path"], {"applications": []})
    return paths


def test_ucl_reuses_directory_budget_for_24_details_after_first_run():
    directory = page(
        "".join(card(f"Example {i} MSc", route=f"example-{i}-msc") for i in range(30)),
        total=30,
    )
    calls = []

    def fetch(url):
        calls.append(url)
        if url == UCL_URL:
            return directory
        number = url.rsplit("/", 1)[-1].split("-")[1]
        return HTML.replace("Advanced Materials Science", f"Example {number}")

    first = UCLAdapter(30, 30).parse_catalog_from_fetcher(fetch)
    assert len(calls) == 6  # Directory + five details, within refresh-day allowance.
    second = UCLAdapter(30, 30)
    second.prepare_discovery({"adapterState": first.adapter_state})
    calls.clear()
    result = second.parse_catalog_from_fetcher(fetch)
    assert len(calls) == 24 and UCL_URL not in calls
    assert result.diagnostics["detailQueue"]["neverChecked"] == 1


@pytest.mark.parametrize("school", ["ucl", "edinburgh", "toronto"])
def test_three_runs_advance_queue_and_preserve_unvisited_candidates(tmp_path, school):
    factory, source, directories = school_case(school)
    paths = paths_for(tmp_path)
    visited = []
    previous_candidates = {}
    old_watch_hash = None
    for run in range(3):
        calls = []

        def fetch(url, calls=calls):
            calls.append(url)
            return source(url)

        report = discover_programmes(factory(), fetcher=fetch, **paths)
        details = [url for url in calls if url not in directories]
        assert len(details) == 1
        assert details[0] not in visited
        visited += details
        if run and school != "toronto":
            assert not set(calls) & directories
        state = read_json(paths["state_path"])["universities"][factory().university_id]
        assert state["adapterDiagnostics"]["detailQueue"]["neverChecked"] == 2 - run
        if school == "ucl":
            if old_watch_hash:
                assert state["watchedWindowSourceHash"] == old_watch_hash
            old_watch_hash = state["watchedWindowSourceHash"]
        items = read_json(paths["candidates_path"])["items"]
        for item in items:
            if item["id"] in previous_candidates and item["sourceUrl"] not in details:
                assert item == previous_candidates[item["id"]]
        previous_candidates = {item["id"]: item for item in items}
        assert report["recordDiff"]["disappearedWindowIds"] == []
    assert read_json(paths["programs_path"]) == {"programs": []}
    assert read_json(paths["applications_path"]) == {"applications": []}


@pytest.mark.parametrize("school", ["ucl", "edinburgh", "toronto"])
def test_dry_run_does_not_commit_queue_or_candidate_progress(tmp_path, school):
    factory, source, directories = school_case(school)
    paths = paths_for(tmp_path)
    discover_programmes(factory(), fetcher=source, **paths)
    before = {path: path.read_bytes() for path in paths.values() if path.exists()}
    dry_calls = []

    def dry_fetch(url):
        dry_calls.append(url)
        return source(url)

    discover_programmes(factory(), fetcher=dry_fetch, dry_run=True, **paths)
    assert all(path.read_bytes() == data for path, data in before.items())
    actual_calls = []

    def actual_fetch(url):
        actual_calls.append(url)
        return source(url)

    discover_programmes(factory(), fetcher=actual_fetch, **paths)
    assert [url for url in actual_calls if url not in directories] == [
        url for url in dry_calls if url not in directories
    ]


@pytest.mark.parametrize("school", ["ucl", "edinburgh", "toronto"])
def test_blocked_detail_saves_progress_and_next_run_visits_another_task(
    tmp_path, school
):
    factory, source, directories = school_case(school)
    paths = paths_for(tmp_path)
    failed = []

    def blocked(url):
        if url in directories:
            return source(url)
        failed.append(url)
        raise FetchFailure("rate limited", kind="rate-limited", status_code=429)

    discover_programmes(factory(), fetcher=blocked, **paths)
    state = read_json(paths["state_path"])["universities"][factory().university_id]
    assert state["adapterState"]["detailQueue"][failed[0]]["status"] == "rate-limited"

    def resumed(url):
        assert url not in failed
        return source(url)

    discover_programmes(factory(), fetcher=resumed, **paths)
