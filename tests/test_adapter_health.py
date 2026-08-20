from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from gradwindow.adapter_health import update_adapter_health
from gradwindow.programme_adapters.base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)
from gradwindow.programme_discovery import discover_programmes


def _paths(tmp_path):
    health_path = tmp_path / "programme-adapter-health.json"
    report_path = tmp_path / "programme-adapter-health.md"
    catalog_path = tmp_path / "programme-catalog-state.json"
    universities_path = tmp_path / "universities.json"
    catalog_path.write_text(
        json.dumps({"universities": {}}),
        encoding="utf-8",
    )
    universities_path.write_text(
        json.dumps(
            {
                "universities": [
                    {"id": "example-university", "school": "Example University"}
                ]
            }
        ),
        encoding="utf-8",
    )
    return health_path, report_path, catalog_path, universities_path


def _success(checked_at: datetime, **overrides) -> dict:
    report = {
        "status": "ok",
        "adapter": "example",
        "universityId": "example-university",
        "sourceUrl": "https://example.edu/programmes",
        "checkedAt": checked_at.isoformat(),
        "catalogueStatus": "ok",
        "windowStatus": "monitoring",
        "catalogProgrammes": 100,
        "observedWindowCount": 0,
        "exactWindowCount": 0,
        "missingOpeningDateCount": 0,
        "programmesWithoutDeadlines": 100,
        "programmesNeedingReview": 100,
        "limitationReason": "No exact dates are currently published.",
        "windowFingerprint": "windows-a",
        "watchedWindowSourceHash": "source-a",
        "watchedWindowSourceFingerprintVersion": 2,
    }
    report.update(overrides)
    return report


def _update(tmp_path, reports, now):
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    return update_adapter_health(
        reports,
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=now,
    )


def test_monitoring_without_exact_windows_is_healthy(tmp_path) -> None:
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)

    payload = _update(tmp_path, [_success(now)], now)

    entry = payload["universities"]["example-university"]
    assert entry["windowStatus"] == "monitoring"
    assert entry["healthStatus"] == "ok"
    assert entry["alerts"] == []
    assert payload["meta"]["summary"]["monitoringWithoutExactWindows"] == 1
    assert payload["meta"]["summary"]["needsMaintenance"] == 0


def test_identity_mismatch_warning_preserves_partial_success_and_alerts(
    tmp_path,
) -> None:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    warning = {
        "reason": "PROGRAMME_ID_MISMATCH",
        "message": "One official application row needs identity review.",
        "sourceUrl": "https://example.edu/apply",
        "programmeKeys": ["new programme"],
    }

    payload = _update(
        tmp_path,
        [_success(now, adapterWarnings=[warning])],
        now,
    )

    entry = payload["universities"]["example-university"]
    assert entry["catalogueStatus"] == "ok"
    assert entry["reasonCategories"] == ["PROGRAMME_ID_MISMATCH"]
    assert [alert["type"] for alert in entry["alerts"]] == ["programme-id-mismatch"]
    assert entry["alerts"][0]["category"] == "data-integrity"


def test_parser_and_unknown_degree_warnings_are_data_integrity_alerts(tmp_path) -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    warnings = [
        {
            "reason": "PARSER_ERROR",
            "message": "One official detail page no longer matches the parser.",
        },
        {
            "reason": "UNKNOWN_DEGREE_CODE",
            "message": "An official graduate degree code is unclassified.",
        },
    ]

    payload = _update(
        tmp_path,
        [_success(now, adapterWarnings=warnings)],
        now,
    )

    alerts = payload["universities"]["example-university"]["alerts"]
    assert [alert["type"] for alert in alerts] == [
        "partial-parser-error",
        "unknown-degree-code",
    ]
    assert all(alert["category"] == "data-integrity" for alert in alerts)


def test_failure_reason_is_preserved_for_transport_diagnosis(tmp_path) -> None:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    failure = {
        "status": "error",
        "adapter": "example",
        "universityId": "example-university",
        "sourceUrl": "https://example.edu/programmes",
        "errorType": "OfficialSourceTransportError",
        "reason": "TRANSPORT_ERROR",
        "message": "Official page returned HTTP 403",
        "checkedAt": now.isoformat(),
    }

    payload = _update(tmp_path, [failure], now)

    entry = payload["universities"]["example-university"]
    assert entry["lastError"]["reason"] == "TRANSPORT_ERROR"
    assert entry["reasonCategories"] == ["TRANSPORT_ERROR"]


def test_two_failures_and_stale_success_create_one_school_level_alert_set(
    tmp_path,
) -> None:
    start = datetime(2026, 7, 24, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)

    update_adapter_health(
        [_success(start)],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start,
    )
    failure = {
        "status": "error",
        "adapter": "example",
        "universityId": "example-university",
        "sourceUrl": "https://example.edu/programmes",
        "errorType": "RuntimeError",
        "message": "HTTP 403",
    }
    update_adapter_health(
        [{**failure, "checkedAt": (start + timedelta(hours=24)).isoformat()}],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(hours=24),
    )
    payload = update_adapter_health(
        [{**failure, "checkedAt": (start + timedelta(hours=49)).isoformat()}],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(hours=49),
    )

    entry = payload["universities"]["example-university"]
    assert entry["healthStatus"] == "needs-maintenance"
    assert [item["type"] for item in entry["alerts"]] == ["consecutive-failures"]
    assert payload["meta"]["summary"]["needsMaintenance"] == 1
    assert payload["meta"]["summary"]["activeAlerts"] == 1
    assert payload["meta"]["summary"]["unavailableAdapters"] == 1
    assert payload["meta"]["summary"]["dataIntegrityRisks"] == 0
    assert payload["meta"]["notificationChanged"] is True
    assert payload["meta"]["notificationDue"] is True
    assert payload["meta"]["notificationReason"] == "alerts-opened"
    report = report_path.read_text(encoding="utf-8")
    assert report.count("| Example University |") == 1

    unchanged = update_adapter_health(
        [{**failure, "checkedAt": (start + timedelta(hours=73)).isoformat()}],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(hours=73),
    )
    assert unchanged["meta"]["notificationChanged"] is False
    assert unchanged["meta"]["notificationDue"] is False

    weekly = update_adapter_health(
        [{**failure, "checkedAt": (start + timedelta(hours=217)).isoformat()}],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(hours=217),
    )
    assert weekly["meta"]["notificationChanged"] is False
    assert weekly["meta"]["notificationDue"] is True
    assert weekly["meta"]["notificationReason"] == "weekly-reminder"

    cleared = update_adapter_health(
        [_success(start + timedelta(hours=241))],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(hours=241),
    )
    assert cleared["meta"]["summary"]["needsMaintenance"] == 0
    assert cleared["meta"]["notificationDue"] is True
    assert cleared["meta"]["notificationReason"] == "alerts-cleared"


def test_source_fingerprint_version_change_resets_baseline_without_alert(
    tmp_path,
) -> None:
    start = datetime(2026, 7, 24, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)

    update_adapter_health(
        [
            _success(
                start,
                watchedWindowSourceHash="legacy-source",
                watchedWindowSourceFingerprintVersion=1,
            )
        ],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start,
    )
    for offset in (1, 2):
        payload = update_adapter_health(
            [
                _success(
                    start + timedelta(days=offset),
                    watchedWindowSourceHash="signal-source",
                    watchedWindowSourceFingerprintVersion=2,
                )
            ],
            health_path=health_path,
            report_path=report_path,
            catalog_state_path=catalog_path,
            universities_path=universities_path,
            now=start + timedelta(days=offset),
        )

    entry = payload["universities"]["example-university"]
    assert entry["stableWatchedWindowSourceHash"] == "signal-source"
    assert entry["pendingWatchedWindowSourceHash"] is None
    assert entry["unparsedSourceChange"] is None
    assert entry["alerts"] == []


def test_confirmed_source_change_without_parser_change_requires_maintenance(
    tmp_path,
) -> None:
    start = datetime(2026, 7, 24, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)

    for offset, source_hash in ((0, "source-a"), (1, "source-b"), (2, "source-b")):
        payload = update_adapter_health(
            [
                _success(
                    start + timedelta(days=offset),
                    watchedWindowSourceHash=source_hash,
                )
            ],
            health_path=health_path,
            report_path=report_path,
            catalog_state_path=catalog_path,
            universities_path=universities_path,
            now=start + timedelta(days=offset),
        )

    entry = payload["universities"]["example-university"]
    assert [item["type"] for item in entry["alerts"]] == ["unparsed-source-change"]
    assert payload["meta"]["summary"]["needsMaintenance"] == 1


def test_exact_window_drop_remains_alerted_against_healthy_baseline(tmp_path) -> None:
    start = datetime(2026, 7, 25, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    update_adapter_health(
        [
            _success(
                start,
                windowStatus="exact",
                observedWindowCount=4,
                exactWindowCount=4,
                programmesWithoutDeadlines=96,
            )
        ],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start,
    )

    payload = update_adapter_health(
        [
            _success(
                start + timedelta(days=1),
                windowStatus="partial",
                observedWindowCount=4,
                exactWindowCount=3,
                missingOpeningDateCount=1,
                recordDiff={
                    "previous": {"programmes": 100, "windows": 4},
                    "current": {"programmes": 100, "windows": 3},
                    "disappearedProgrammeIds": [],
                    "disappearedWindowIds": ["example-msc::Fall 2027::Final::all"],
                },
            )
        ],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(days=1),
    )

    alerts = payload["universities"]["example-university"]["alerts"]
    assert [item["type"] for item in alerts] == ["exact-window-drop"]
    assert alerts[0]["category"] == "data-integrity"
    assert alerts[0]["reason"] == "SOURCE_RECORD_REMOVED"
    assert alerts[0]["details"]["disappearedWindowIds"] == [
        "example-msc::Fall 2027::Final::all"
    ]
    assert payload["meta"]["summary"]["dataIntegrityRisks"] == 1


def test_observed_window_drop_is_reported_even_when_exact_count_is_stable(
    tmp_path,
) -> None:
    start = datetime(2026, 8, 10, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    update_adapter_health(
        [
            _success(
                start,
                windowStatus="partial",
                observedWindowCount=45,
                exactWindowCount=2,
            )
        ],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start,
    )

    payload = update_adapter_health(
        [
            _success(
                start + timedelta(days=1),
                windowStatus="partial",
                observedWindowCount=2,
                exactWindowCount=2,
            )
        ],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=start + timedelta(days=1),
    )

    alerts = payload["universities"]["example-university"]["alerts"]
    assert [item["type"] for item in alerts] == ["observed-window-drop"]
    assert alerts[0]["category"] == "data-integrity"


def test_previous_success_replaces_peak_baseline_but_keeps_historical_max(
    tmp_path,
) -> None:
    start = datetime(2026, 8, 10, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    kwargs = {
        "health_path": health_path,
        "report_path": report_path,
        "catalog_state_path": catalog_path,
        "universities_path": universities_path,
    }
    update_adapter_health(
        [_success(start, observedWindowCount=52, exactWindowCount=52)],
        now=start,
        **kwargs,
    )
    second = update_adapter_health(
        [
            _success(
                start + timedelta(days=1),
                observedWindowCount=42,
                exactWindowCount=42,
            )
        ],
        now=start + timedelta(days=1),
        **kwargs,
    )
    third = update_adapter_health(
        [
            _success(
                start + timedelta(days=2),
                observedWindowCount=42,
                exactWindowCount=42,
            )
        ],
        now=start + timedelta(days=2),
        **kwargs,
    )

    assert (
        second["universities"]["example-university"]["baselineExactWindowCount"] == 52
    )
    entry = third["universities"]["example-university"]
    assert entry["baselineExactWindowCount"] == 42
    assert entry["historicalMaxExactWindowCount"] == 52
    assert entry["alerts"] == []


def test_cycle_transition_does_not_compare_new_intake_to_old_intake_peak(
    tmp_path,
) -> None:
    start = datetime(2026, 8, 10, tzinfo=timezone.utc)
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    kwargs = {
        "health_path": health_path,
        "report_path": report_path,
        "catalog_state_path": catalog_path,
        "universities_path": universities_path,
    }
    fall_2026 = {
        "2026:fall:09": {
            "intakes": ["Fall 2026"],
            "observedWindowCount": 52,
            "exactWindowCount": 52,
            "recurringPolicyWindowCount": 0,
        }
    }
    fall_2027 = {
        "2027:fall:09": {
            "intakes": ["Fall 2027"],
            "observedWindowCount": 42,
            "exactWindowCount": 42,
            "recurringPolicyWindowCount": 0,
        }
    }
    update_adapter_health(
        [
            _success(
                start,
                observedWindowCount=52,
                exactWindowCount=52,
                windowCountsByCycle=fall_2026,
            )
        ],
        now=start,
        **kwargs,
    )
    payload = update_adapter_health(
        [
            _success(
                start + timedelta(days=1),
                observedWindowCount=42,
                exactWindowCount=42,
                windowCountsByCycle=fall_2027,
            )
        ],
        now=start + timedelta(days=1),
        **kwargs,
    )

    entry = payload["universities"]["example-university"]
    assert entry["alerts"] == []
    assert entry["baselineWindowCountsByCycle"] == fall_2026
    assert set(entry["historicalMaxWindowCountsByCycle"]) == {
        "2026:fall:09",
        "2027:fall:09",
    }


def test_expired_window_removal_does_not_create_published_data_risk(tmp_path) -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    report = _success(
        now,
        observedWindowCount=3,
        exactWindowCount=3,
        previousCatalogProgrammes=100,
        disappearedWindowDetails={
            "example-msc::Fall 2026::Final::all": {
                "programmeId": "example-msc",
                "opensAt": "2025-09-01",
                "closesAt": "2026-08-19",
                "sourceUrl": "https://example.edu/msc",
            }
        },
    )
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    health_path.write_text(
        json.dumps(
            {
                "meta": {},
                "universities": {
                    "example-university": {
                        "catalogProgrammes": 100,
                        "observedWindowCount": 4,
                        "exactWindowCount": 4,
                        "baselineObservedWindowCount": 4,
                        "baselineExactWindowCount": 4,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    payload = update_adapter_health(
        [report],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=now,
    )

    entry = payload["universities"]["example-university"]
    assert entry["expiredDisappearedWindowIds"] == [
        "example-msc::Fall 2026::Final::all"
    ]
    assert entry["alerts"] == []


def test_expired_programme_removal_does_not_create_published_data_risk(
    tmp_path,
) -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    report = _success(
        now,
        catalogProgrammes=99,
        observedWindowCount=3,
        exactWindowCount=3,
        recordDiff={
            "previous": {"programmes": 100, "windows": 4},
            "current": {"programmes": 99, "windows": 3},
            "disappearedProgrammeIds": ["expired-msc"],
            "disappearedWindowIds": ["expired-msc::Fall 2026::Main::all"],
        },
        windowRemovalAssessmentAvailable=True,
        disappearedWindowDetails={
            "expired-msc::Fall 2026::Main::all": {
                "programmeId": "expired-msc",
                "closesAt": "2026-08-19",
            }
        },
        disappearedProgrammeDetails={
            "expired-msc": {
                "name": "Expired MSc",
                "windowCount": 1,
                "latestClosesAt": "2026-08-19",
            }
        },
    )
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    health_path.write_text(
        json.dumps(
            {
                "meta": {},
                "universities": {
                    "example-university": {
                        "catalogProgrammes": 100,
                        "observedWindowCount": 4,
                        "exactWindowCount": 4,
                        "baselineObservedWindowCount": 4,
                        "baselineExactWindowCount": 4,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    payload = update_adapter_health(
        [report],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=now,
    )

    entry = payload["universities"]["example-university"]
    assert entry["expiredDisappearedProgrammeIds"] == ["expired-msc"]
    assert entry["futureDisappearedProgrammeIds"] == []
    assert entry["unknownDisappearedProgrammeIds"] == []
    assert entry["alerts"] == []


def test_future_programme_removal_remains_a_published_data_risk(tmp_path) -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    report = _success(
        now,
        catalogProgrammes=99,
        observedWindowCount=3,
        exactWindowCount=3,
        recordDiff={
            "previous": {"programmes": 100, "windows": 4},
            "current": {"programmes": 99, "windows": 3},
            "disappearedProgrammeIds": ["future-msc"],
            "disappearedWindowIds": ["future-msc::Fall 2027::Main::all"],
        },
        windowRemovalAssessmentAvailable=True,
        disappearedWindowDetails={
            "future-msc::Fall 2027::Main::all": {
                "programmeId": "future-msc",
                "closesAt": "2027-01-15",
            }
        },
        disappearedProgrammeDetails={
            "future-msc": {
                "name": "Future MSc",
                "windowCount": 1,
                "latestClosesAt": "2027-01-15",
            }
        },
    )
    health_path, report_path, catalog_path, universities_path = _paths(tmp_path)
    health_path.write_text(
        json.dumps(
            {
                "meta": {},
                "universities": {
                    "example-university": {
                        "catalogProgrammes": 100,
                        "observedWindowCount": 4,
                        "exactWindowCount": 4,
                        "baselineObservedWindowCount": 4,
                        "baselineExactWindowCount": 4,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    payload = update_adapter_health(
        [report],
        health_path=health_path,
        report_path=report_path,
        catalog_state_path=catalog_path,
        universities_path=universities_path,
        now=now,
    )

    entry = payload["universities"]["example-university"]
    assert entry["futureDisappearedProgrammeIds"] == ["future-msc"]
    assert [alert["type"] for alert in entry["alerts"]] == [
        "exact-window-drop",
        "observed-window-drop",
        "programme-record-removed",
    ]
    assert entry["alerts"][0]["details"]["futureDisappearedProgrammeIds"] == [
        "future-msc"
    ]


def test_unknown_programme_removal_requires_review(tmp_path) -> None:
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    report = _success(
        now,
        catalogProgrammes=99,
        recordDiff={
            "previous": {"programmes": 100, "windows": 0},
            "current": {"programmes": 99, "windows": 0},
            "disappearedProgrammeIds": ["unknown-msc"],
            "disappearedWindowIds": [],
        },
        windowRemovalAssessmentAvailable=True,
        disappearedProgrammeDetails={
            "unknown-msc": {
                "name": "Unknown MSc",
                "windowCount": 0,
                "latestClosesAt": None,
            }
        },
    )

    payload = _update(tmp_path, [report], now)

    entry = payload["universities"]["example-university"]
    assert entry["unknownDisappearedProgrammeIds"] == ["unknown-msc"]
    assert [alert["type"] for alert in entry["alerts"]] == ["programme-record-removed"]
    assert entry["alerts"][0]["category"] == "data-integrity"


def test_discovery_records_window_watch_fingerprint_and_completion_metrics(
    tmp_path,
) -> None:
    class WatchedAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        window_watch_urls = ("https://example.edu/application-dates",)

        def parse_catalog_from_fetcher(self, fetcher):
            fetcher(self.window_watch_urls[0])
            fetcher(self.catalog_url)
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="Example Faculty",
                        department="Example Department",
                        source_url=self.catalog_url,
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Main",
                                opens_at="2026-08-01",
                                closes_at="2027-01-15",
                            ),
                            DiscoveredWindow(
                                round="Late",
                                closes_at="2027-03-01",
                            ),
                        ],
                        deadline_text="Official dates",
                        parse_status="parsed",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")
    responses = {
        "https://example.edu/application-dates": (
            "<main>Applications open 1 August and close 15 January.</main>"
        ),
        "https://example.edu/programmes": "<main>Example MSc</main>",
    }

    report = discover_programmes(
        WatchedAdapter(),
        programs_path=programs_path,
        applications_path=applications_path,
        candidates_path=tmp_path / "programme-candidates.json",
        window_candidates_path=tmp_path / "window-candidates.json",
        state_path=tmp_path / "programme-catalog-state.json",
        fetcher=responses.__getitem__,
    )

    assert report["watchedWindowSourceHash"]
    assert report["observedWindowCount"] == 2
    assert report["exactWindowCount"] == 1
    assert report["missingOpeningDateCount"] == 1
    assert report["windowStatus"] == "partial"
    assert report["watchedWindowSourceFingerprintVersion"] == 2


def test_discovery_reports_record_level_window_removals(tmp_path) -> None:
    class ChangingAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "September 2027"
        include_final_round = True

        def parse_catalog_from_fetcher(self, _fetcher):
            windows = [
                DiscoveredWindow(
                    round="First",
                    opens_at="2026-09-01",
                    closes_at="2026-12-01",
                    intake=self.intake,
                )
            ]
            if self.include_final_round:
                windows.append(
                    DiscoveredWindow(
                        round="Final",
                        opens_at="2026-09-01",
                        closes_at="2027-02-01",
                        intake=self.intake,
                    )
                )
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="Example Faculty",
                        department="Example Department",
                        source_url=self.catalog_url,
                        application_url="https://example.edu/apply",
                        windows=windows,
                        deadline_text="Official dates",
                        parse_status="parsed",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    candidates_path = tmp_path / "programme-candidates.json"
    window_candidates_path = tmp_path / "window-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")
    adapter = ChangingAdapter()
    kwargs = {
        "programs_path": programs_path,
        "applications_path": applications_path,
        "candidates_path": candidates_path,
        "window_candidates_path": window_candidates_path,
        "state_path": state_path,
        "fetcher": lambda _url: "",
    }

    first = discover_programmes(adapter, **kwargs)
    adapter.include_final_round = False
    second = discover_programmes(adapter, **kwargs)

    assert first["recordDiff"]["disappearedWindowIds"] == []
    assert first["windowCountsByCycle"]["2027:fall:09"] == {
        "intakes": ["September 2027"],
        "observedWindowCount": 2,
        "exactWindowCount": 2,
        "recurringPolicyWindowCount": 0,
    }
    assert second["recordDiff"] == {
        "previous": {"programmes": 1, "windows": 2},
        "current": {"programmes": 1, "windows": 1},
        "disappearedProgrammeIds": [],
        "addedProgrammeIds": [],
        "changedProgrammeIds": ["example-msc"],
        "disappearedWindowIds": ["example-msc::September 2027::Final::all"],
        "addedWindowIds": [],
        "changedWindowIds": [],
    }
    assert second["windowRemovalAssessmentAvailable"] is True
    assert second["disappearedWindowDetails"] == {
        "example-msc::September 2027::Final::all": {
            "programmeId": "example-msc",
            "intake": "September 2027",
            "opensAt": "2026-09-01",
            "closesAt": "2027-02-01",
            "sourceUrl": "https://example.edu/programmes",
            "opensAtBasis": None,
        }
    }


def test_discovery_reports_programme_removal_lifecycle_details(tmp_path) -> None:
    class ChangingAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        intake = "September 2027"
        include_programme = True

        def parse_catalog_from_fetcher(self, _fetcher):
            programmes = []
            if self.include_programme:
                programmes.append(
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="Example Faculty",
                        department="Example Department",
                        source_url=self.catalog_url,
                        application_url="https://example.edu/apply",
                        windows=[
                            DiscoveredWindow(
                                round="Main",
                                opens_at="2026-09-01",
                                closes_at="2027-02-01",
                                intake=self.intake,
                            )
                        ],
                        deadline_text="Official dates",
                        parse_status="parsed",
                    )
                )
            return DiscoveredCatalog(application_opens_at=None, programmes=programmes)

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")
    adapter = ChangingAdapter()
    kwargs = {
        "programs_path": programs_path,
        "applications_path": applications_path,
        "candidates_path": tmp_path / "programme-candidates.json",
        "window_candidates_path": tmp_path / "window-candidates.json",
        "state_path": state_path,
        "fetcher": lambda _url: "",
    }

    discover_programmes(adapter, **kwargs)
    adapter.include_programme = False
    report = discover_programmes(adapter, **kwargs)

    assert report["disappearedProgrammeDetails"] == {
        "example-msc": {
            "name": "Example MSc",
            "degreeType": "MSc",
            "faculty": "Example Faculty",
            "department": "Example Department",
            "parseStatus": "parsed",
            "windowCount": 1,
            "latestClosesAt": "2027-02-01",
            "deadlineHash": report["disappearedProgrammeDetails"]["example-msc"][
                "deadlineHash"
            ],
        }
    }


def test_window_watch_fingerprint_ignores_non_deadline_page_changes(tmp_path) -> None:
    class WatchedAdapter(BaseProgrammeAdapter):
        university_id = "example-university"
        catalog_url = "https://example.edu/programmes"
        window_watch_urls = ("https://example.edu/application-dates",)

        def parse_catalog_from_fetcher(self, fetcher):
            fetcher(self.window_watch_urls[0])
            return DiscoveredCatalog(
                application_opens_at=None,
                programmes=[
                    DiscoveredProgramme(
                        id="example-msc",
                        name="Example MSc",
                        degree_type="MSc",
                        faculty="Example Faculty",
                        department="Example Department",
                        source_url=self.catalog_url,
                        application_url="https://example.edu/apply",
                        windows=[],
                        deadline_text=None,
                        parse_status="unparsed",
                    )
                ],
            )

    programs_path = tmp_path / "programs.json"
    applications_path = tmp_path / "applications.json"
    programs_path.write_text(json.dumps({"programs": []}), encoding="utf-8")
    applications_path.write_text(json.dumps({"applications": []}), encoding="utf-8")

    def report_for(watch_html: str) -> dict:
        responses = {
            "https://example.edu/application-dates": watch_html,
        }
        return discover_programmes(
            WatchedAdapter(),
            programs_path=programs_path,
            applications_path=applications_path,
            candidates_path=tmp_path / "programme-candidates.json",
            window_candidates_path=tmp_path / "window-candidates.json",
            state_path=tmp_path / "programme-catalog-state.json",
            fetcher=responses.__getitem__,
            dry_run=True,
        )

    earlier_signals = "".join(
        f"<p>Programme {index} deadline: 1 January 2027.</p>" for index in range(21)
    )
    first = report_for(
        f"<main>{earlier_signals}<p>Applications close 15 January 2027.</p>"
        "<p>Campus news item A.</p></main>"
    )
    chrome_only = report_for(
        f"<main>{earlier_signals}<p>Applications close 15 January 2027.</p>"
        "<p>Campus news item B.</p></main>"
    )
    deadline_change = report_for(
        f"<main>{earlier_signals}<p>Applications close 16 January 2027.</p>"
        "<p>Campus news item B.</p></main>"
    )

    assert first["watchedWindowSourceHash"] == chrome_only["watchedWindowSourceHash"]
    assert (
        first["watchedWindowSourceHash"] != deadline_change["watchedWindowSourceHash"]
    )
