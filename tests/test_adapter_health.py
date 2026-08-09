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
    assert payload["meta"]["summary"]["dataIntegrityRisks"] == 1


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
