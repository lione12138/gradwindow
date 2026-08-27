from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .adapter_health import update_adapter_health
from .approvals import (
    approve_official_adapter_window_candidates,
    approve_programme_candidates,
    approve_window,
)
from .coverage import generate_coverage
from .deadlines import update_deadlines
from .generic_discovery_batch import (
    refresh_generic_discovery_report,
    run_assisted_discovery_entry,
    run_generic_discovery_batch,
)
from .generic_seed_discovery import run_generic_seed_discovery
from .intakes import migrate_application_intakes
from .io import read_json
from .monitor import monitor_universities, print_summary
from .paths import (
    APPLICATION_SOURCE_STATE_PATH,
    GENERIC_PROGRAMME_DISCOVERY_CONFIG_PATH,
    PROGRAMME_CANDIDATES_PATH,
    SITE_DIR,
    UNIVERSITIES_PATH,
)
from .predictions import generate_predictions
from .programme_adapters.generic import GenericProgrammeAdapter, GenericProgrammeConfig
from .programme_adapters.registry import PROGRAMME_ADAPTERS
from .programme_discovery import discover_programmes
from .published_data_audit import generate_published_data_audit
from .readme import generate_readmes
from .recurring_windows import generate_recurring_windows
from .refresh_status import generate_refresh_status
from .review import generate_review_outputs
from .schemas import export_schemas
from .site import build_site
from .source_monitor import DEFAULT_MAX_SOURCE_URLS, monitor_application_sources
from .validation import validate_data

DEDICATED_ADAPTER_TIMEOUT_SECONDS = 900
_ADAPTER_WORKER_CODE = "from gradwindow.cli import main; main()"


def main() -> None:
    parser = argparse.ArgumentParser(description="GradWindow data pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate public datasets")
    build = subparsers.add_parser("build-site", help="Build the deployable site")
    build.add_argument("--output", type=Path, default=SITE_DIR)
    monitor = subparsers.add_parser("monitor", help="Check university pages")
    monitor.add_argument("--workers", type=int, default=16)
    source_monitor = subparsers.add_parser(
        "monitor-sources", help="Check exact application-window source pages"
    )
    source_monitor.add_argument("--workers", type=int, default=8)
    source_monitor.add_argument(
        "--max-urls",
        type=int,
        default=DEFAULT_MAX_SOURCE_URLS,
    )
    programme_discovery = subparsers.add_parser(
        "discover-programmes",
        help="Discover new taught programmes from supported official catalogues",
    )
    programme_discovery.add_argument(
        "--university",
        choices=("all", *tuple(PROGRAMME_ADAPTERS)),
        default="cuhk",
    )
    programme_discovery.add_argument("--dry-run", action="store_true")
    adapter_worker = subparsers.add_parser(
        "_pipeline-adapter",
        help=argparse.SUPPRESS,
    )
    adapter_worker.add_argument(
        "--university",
        choices=tuple(PROGRAMME_ADAPTERS),
        required=True,
    )
    adapter_worker.add_argument("--dry-run", action="store_true")
    generic_discovery = subparsers.add_parser(
        "discover-generic-programmes",
        help="Discover taught master's programmes from official seed pages",
    )
    generic_discovery.add_argument("--university", required=True)
    generic_discovery.add_argument(
        "--seed",
        action="append",
        help="Official catalogue or programme page URL. Can be repeated.",
    )
    generic_discovery.add_argument(
        "--prefix",
        help="Programme id prefix. Defaults to a slug derived from the university id.",
    )
    generic_discovery.add_argument("--default-intake", default="September 2026")
    generic_discovery.add_argument("--default-application-opens-at")
    generic_discovery.add_argument("--minimum-closes-at", default="2025-07-01")
    generic_discovery.add_argument("--min-programmes", type=int, default=1)
    generic_discovery.add_argument("--max-pages", type=int, default=25)
    generic_discovery.add_argument("--dry-run", action="store_true")
    generic_batch = subparsers.add_parser(
        "discover-generic-batch",
        help="Run configured generic programme discovery seed pages",
    )
    generic_batch.add_argument("--dry-run", action="store_true")
    generic_batch.add_argument(
        "--replace-existing",
        action="store_true",
        help="Remove pending candidates from this configured batch before rerunning.",
    )
    generic_batch.add_argument(
        "--only",
        action="append",
        help="Limit to a university id or configured name. Can be repeated.",
    )
    generic_seeds = subparsers.add_parser(
        "discover-generic-seeds",
        help="Audit configured generic discovery seeds and recommend replacements",
    )
    generic_seeds.add_argument(
        "--only",
        action="append",
        help="Limit to a university id or configured name. Can be repeated.",
    )
    generic_seeds.add_argument("--max-candidate-seeds", type=int, default=12)
    subparsers.add_parser(
        "refresh-generic-report",
        help="Refresh generic discovery review buckets without network requests",
    )
    assisted_discovery = subparsers.add_parser(
        "discover-assisted",
        help="Search official domains and use DeepSeek to extract review candidates",
    )
    assisted_discovery.add_argument("--university", required=True)
    assisted_discovery.add_argument("--dry-run", action="store_true")
    deadlines = subparsers.add_parser(
        "update-deadlines", help="Run configured programme parsers"
    )
    deadlines.add_argument("--dry-run", action="store_true")
    pipeline = subparsers.add_parser("pipeline", help="Run the daily pipeline")
    pipeline.add_argument("--workers", type=int, default=16)
    pipeline.add_argument(
        "--source-monitor-max-urls",
        type=int,
        default=DEFAULT_MAX_SOURCE_URLS,
    )
    pipeline.add_argument("--skip-monitor", action="store_true")
    pipeline.add_argument("--skip-build", action="store_true")
    subparsers.add_parser("coverage", help="Generate QS top-200 coverage metrics")
    subparsers.add_parser(
        "predictions", help="Generate non-official next-cycle estimates"
    )
    subparsers.add_parser(
        "recurring-windows",
        help="Publish official recurring policies with mapped cycle years",
    )
    subparsers.add_parser(
        "migrate-intakes", help="Add structured intake details to applications"
    )
    subparsers.add_parser(
        "audit-published-data",
        help="Audit published windows against intake timing and adapter snapshots",
    )
    subparsers.add_parser(
        "export-schemas", help="Export Pydantic contracts as JSON Schema"
    )
    subparsers.add_parser(
        "readme", help="Generate English and Chinese result dashboards"
    )
    approve = subparsers.add_parser(
        "approve-window", help="Promote a reviewed exact-window candidate"
    )
    approve.add_argument("candidate_id")
    approve.add_argument("--reviewer", required=True)
    approve_programmes = subparsers.add_parser(
        "approve-programmes",
        help="Promote reviewed programme candidates with exact windows",
    )
    approve_programmes.add_argument("--university", required=True)
    approve_programmes.add_argument("--reviewer", required=True)
    approve_programmes.add_argument(
        "--include-unparsed",
        action="store_true",
        help="Also promote candidates whose parseStatus is not parsed",
    )
    approve_adapter_windows = subparsers.add_parser(
        "approve-adapter-windows",
        help="Promote all complete official exact-window candidates from adapters",
    )
    approve_adapter_windows.add_argument("--reviewer", required=True)
    args = parser.parse_args()

    if args.command == "validate":
        _validate_or_exit()
    elif args.command == "build-site":
        generate_predictions()
        generate_recurring_windows()
        _validate_or_exit()
        generate_coverage()
        generate_published_data_audit()
        print(f"Wrote site: {build_site(args.output)}")
    elif args.command == "monitor":
        print_summary(monitor_universities(workers=args.workers))
    elif args.command == "monitor-sources":
        print_summary(
            monitor_application_sources(
                workers=args.workers,
                max_urls=args.max_urls,
                progress_callback=_source_monitor_progress,
            )
        )
    elif args.command == "discover-programmes":
        if args.university == "all":
            report, _successful_ids = _run_dedicated_discovery(dry_run=args.dry_run)
            if not args.dry_run:
                update_adapter_health(report)
        else:
            report = discover_programmes(
                PROGRAMME_ADAPTERS[args.university](),
                dry_run=args.dry_run,
            )
        if not args.dry_run:
            generate_recurring_windows()
        print(json.dumps(report, ensure_ascii=False))
    elif args.command == "_pipeline-adapter":
        report = _pipeline_discovery_report(
            args.university,
            PROGRAMME_ADAPTERS[args.university],
            dry_run=args.dry_run,
        )
        print(json.dumps(report, ensure_ascii=False), flush=True)
    elif args.command == "discover-generic-programmes":
        university = _university_by_id(args.university)
        seed_urls = tuple(
            args.seed
            or [
                university.get("admissionsUrl") or university.get("homepageUrl") or "",
            ]
        )
        adapter = GenericProgrammeAdapter(
            GenericProgrammeConfig(
                university_id=args.university,
                school_prefix=args.prefix or _generic_prefix(args.university),
                seed_urls=tuple(url for url in seed_urls if url),
                official_domains=tuple(university.get("officialDomains", [])),
                default_application_url=(
                    university.get("admissionsUrl")
                    or university.get("homepageUrl")
                    or ""
                ),
                default_intake=args.default_intake,
                default_application_opens_at=args.default_application_opens_at,
                minimum_closes_at=args.minimum_closes_at,
                minimum_expected_programmes=args.min_programmes,
                max_detail_pages=args.max_pages,
            )
        )
        print(
            json.dumps(
                discover_programmes(adapter, dry_run=args.dry_run),
                ensure_ascii=False,
            )
        )
    elif args.command == "discover-generic-batch":
        report = run_generic_discovery_batch(
            dry_run=args.dry_run,
            replace_existing=args.replace_existing,
            only=set(args.only) if args.only else None,
        )
        if not args.dry_run:
            generate_recurring_windows()
        print(json.dumps(report["summary"], ensure_ascii=False))
    elif args.command == "discover-generic-seeds":
        report = run_generic_seed_discovery(
            only=set(args.only) if args.only else None,
            max_candidate_seeds=args.max_candidate_seeds,
        )
        print(json.dumps(report["summary"], ensure_ascii=False))
    elif args.command == "discover-assisted":
        config = read_json(GENERIC_PROGRAMME_DISCOVERY_CONFIG_PATH)
        entry = next(
            (
                item
                for item in config.get("schools", [])
                if args.university in {item.get("universityId"), item.get("name")}
            ),
            None,
        )
        if entry is None:
            raise SystemExit(
                f"No generic discovery entry configured for {args.university}"
            )
        report = run_assisted_discovery_entry(
            entry,
            _university_by_id(entry["universityId"]),
            dry_run=args.dry_run,
        )
        print(json.dumps(report, ensure_ascii=False))
        if report.get("status") == "error":
            raise SystemExit(1)
    elif args.command == "update-deadlines":
        report = update_deadlines(dry_run=args.dry_run)
        print(json.dumps(report, ensure_ascii=False))
        if any(item["status"] == "error" for item in report["results"]):
            raise SystemExit(1)
    elif args.command == "coverage":
        generate_predictions()
        coverage = generate_coverage()
        print(json.dumps(coverage["summary"], ensure_ascii=False))
    elif args.command == "predictions":
        predictions = generate_predictions()
        print(f"Wrote {len(predictions['predictions'])} non-official predictions.")
    elif args.command == "recurring-windows":
        report = generate_recurring_windows()
        print(json.dumps(report, ensure_ascii=False))
    elif args.command == "migrate-intakes":
        payload = migrate_application_intakes()
        generate_predictions()
        print(f"Migrated {len(payload['applications'])} structured intake records.")
    elif args.command == "audit-published-data":
        audit = generate_published_data_audit()
        print(json.dumps(audit["summary"], ensure_ascii=False))
    elif args.command == "export-schemas":
        written = export_schemas()
        print(f"Wrote {len(written)} JSON Schema files.")
    elif args.command == "readme":
        written = generate_readmes()
        print(f"Wrote README dashboards: {written[0].name}, {written[1].name}.")
    elif args.command == "approve-window":
        record = approve_window(args.candidate_id, args.reviewer)
        generate_predictions()
        generate_recurring_windows()
        coverage = generate_coverage()
        generate_readmes()
        generate_published_data_audit()
        print(
            f"Approved {record['id']}; "
            f"{coverage['summary']['verifiedWindows']} verified windows tracked."
        )
    elif args.command == "approve-programmes":
        if args.university == "all":
            report = _approve_all_programmes(
                reviewer=args.reviewer,
                parsed_only=not args.include_unparsed,
            )
        else:
            report = approve_programme_candidates(
                university_id=args.university,
                reviewer=args.reviewer,
                parsed_only=not args.include_unparsed,
            )
        refresh_generic_discovery_report()
        generate_predictions()
        generate_recurring_windows()
        print(json.dumps(report, ensure_ascii=False))
    elif args.command == "approve-adapter-windows":
        report = approve_official_adapter_window_candidates(
            reviewer=args.reviewer,
        )
        generate_predictions()
        generate_recurring_windows()
        print(json.dumps(report, ensure_ascii=False))
    elif args.command == "refresh-generic-report":
        report = refresh_generic_discovery_report()
        print(json.dumps(report["summary"], ensure_ascii=False))
    elif args.command == "pipeline":
        generate_predictions()
        generate_recurring_windows()
        _validate_or_exit()
        if not args.skip_monitor:
            _print_pipeline_progress("university-monitor", "started")
            university_monitor_summary = monitor_universities(workers=args.workers)
            print_summary(university_monitor_summary)
            _print_pipeline_progress(
                "university-monitor",
                "completed",
                summary=university_monitor_summary,
            )
            _print_pipeline_progress(
                "application-source-monitor",
                "started",
                maxUrls=args.source_monitor_max_urls,
            )
            source_monitor_summary = monitor_application_sources(
                workers=max(1, args.workers // 2),
                max_urls=args.source_monitor_max_urls,
                progress_callback=_source_monitor_progress,
            )
            print_summary(source_monitor_summary)
            _print_pipeline_progress(
                "application-source-monitor",
                "completed",
                summary=source_monitor_summary,
            )
            _print_pipeline_progress("dedicated-discovery", "started")
            discovery_reports, successful_dedicated_ids = _run_dedicated_discovery()
            _print_pipeline_progress(
                "dedicated-discovery",
                "completed",
                total=len(discovery_reports),
                successful=len(successful_dedicated_ids),
            )
            for discovery_report in discovery_reports:
                print(json.dumps(discovery_report, ensure_ascii=False))
            adapter_health = update_adapter_health(discovery_reports)
            print(
                json.dumps(
                    {"adapterHealth": adapter_health["meta"]["summary"]},
                    ensure_ascii=False,
                )
            )
            generic_report = run_generic_discovery_batch(
                successful_dedicated_university_ids=successful_dedicated_ids
            )
            print(json.dumps(generic_report["summary"], ensure_ascii=False))
            auto_programme_report = _auto_approve_programmes(
                successful_dedicated_ids,
                reviewer="automated-official-source-policy",
            )
            auto_window_report = approve_official_adapter_window_candidates(
                reviewer="automated-official-source-policy",
                university_ids=successful_dedicated_ids,
            )
            print(
                json.dumps(
                    {
                        "autoPublishedProgrammes": auto_programme_report,
                        "autoPublishedAdapterWindows": auto_window_report,
                    },
                    ensure_ascii=False,
                )
            )
            generate_recurring_windows()
        report = update_deadlines()
        if any(item["status"] == "error" for item in report["results"]):
            raise SystemExit(1)
        generate_predictions()
        generate_recurring_windows()
        _validate_or_exit()
        coverage = generate_coverage()
        generate_readmes()
        published_audit = generate_published_data_audit()
        print(
            json.dumps(
                {"publishedDataAudit": published_audit["summary"]},
                ensure_ascii=False,
            )
        )
        print(
            "Top-200 coverage: "
            f"{coverage['summary']['policiesVerified']}/200 policies, "
            f"{coverage['summary']['universitiesWithWindows']}/200 with windows"
        )
        review_report, review_summary = generate_review_outputs(
            source_state_path=APPLICATION_SOURCE_STATE_PATH
        )
        print(
            f"Wrote review report: {review_report} "
            f"({review_summary['pendingReview']} pending)"
        )
        if not args.skip_monitor:
            refresh_status = generate_refresh_status()
            print(
                "Recorded successful monitoring run: "
                f"{refresh_status['lastSuccessfulMonitoringRun']}"
            )
        if not args.skip_build:
            print(f"Wrote site: {build_site()}")


def _validate_or_exit() -> dict[str, int]:
    errors, summary = validate_data()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(
        "Validated "
        f"{summary['universities']} universities, "
        f"{summary['admissionsCandidates']} admissions candidates "
        f"({summary['curatedAdmissions']} curated), and "
        f"{summary['verifiedWindows']} verified windows with "
        f"{summary['recurringPolicyWindows']} recurring-policy windows, "
        f"{summary['predictedWindows']} next-cycle predictions and "
        f"{summary['evidenceSnapshots']} evidence snapshots; "
        f"{summary['enabledParsers']} enabled parsers; "
        f"{summary['legacyConfiguredOpeningWindows']} legacy configured openings."
    )
    return summary


def _pipeline_discovery_report(
    name: str,
    adapter_factory,
    *,
    dry_run: bool = False,
) -> dict:
    adapter = None
    try:
        adapter = adapter_factory()
        report = discover_programmes(adapter, dry_run=dry_run)
        report.setdefault("adapter", name)
        return report
    except Exception as exc:
        report = {
            "status": "error",
            "adapter": name,
            "universityId": getattr(
                adapter,
                "university_id",
                getattr(adapter_factory, "university_id", None),
            ),
            "sourceUrl": getattr(
                adapter,
                "catalog_url",
                getattr(adapter_factory, "catalog_url", None),
            ),
            "errorType": type(exc).__name__,
            "message": str(exc),
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "dryRun": dry_run,
        }
        if reason := getattr(exc, "reason", None):
            report["reason"] = reason
        if diagnostics := getattr(exc, "transport_diagnostics", None):
            report["adapterDiagnostics"] = {"transport": diagnostics}
        return report


def _run_dedicated_discovery(
    *,
    dry_run: bool = False,
) -> tuple[list[dict], set[str]]:
    timeout_seconds = _dedicated_adapter_timeout_seconds()
    reports = []
    total = len(PROGRAMME_ADAPTERS)
    for index, (name, adapter_factory) in enumerate(PROGRAMME_ADAPTERS.items(), 1):
        _print_pipeline_progress(
            "dedicated-adapter",
            "started",
            adapter=name,
            completed=index - 1,
            total=total,
            timeoutSeconds=timeout_seconds,
        )
        started = time.monotonic()
        report = _run_dedicated_adapter_process(
            name,
            adapter_factory,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
        )
        reports.append(report)
        _print_pipeline_progress(
            "dedicated-adapter",
            "completed",
            adapter=name,
            adapterStatus=report.get("status"),
            completed=index,
            total=total,
            durationSeconds=round(time.monotonic() - started, 1),
        )
    successful_university_ids = {
        report["universityId"]
        for report in reports
        if report.get("status") == "ok" and report.get("universityId")
    }
    return reports, successful_university_ids


def _run_dedicated_adapter_process(
    name: str,
    adapter_factory,
    *,
    dry_run: bool = False,
    timeout_seconds: int = DEDICATED_ADAPTER_TIMEOUT_SECONDS,
) -> dict:
    command = [
        sys.executable,
        "-c",
        _ADAPTER_WORKER_CODE,
        "_pipeline-adapter",
        "--university",
        name,
    ]
    if dry_run:
        command.append("--dry-run")
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _adapter_process_error_report(
            name,
            adapter_factory,
            error_type="TimeoutError",
            message=(
                f"Dedicated adapter exceeded the {timeout_seconds}-second "
                "pipeline limit."
            ),
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
        )

    if result.stderr:
        print(result.stderr, file=sys.stderr, end="", flush=True)
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or not output_lines:
        detail = " ".join(result.stderr.split())[-500:] or (
            f"worker exited with status {result.returncode}"
        )
        return _adapter_process_error_report(
            name,
            adapter_factory,
            error_type="AdapterProcessError",
            message=detail,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
        )
    try:
        report = json.loads(output_lines[-1])
    except json.JSONDecodeError as exc:
        return _adapter_process_error_report(
            name,
            adapter_factory,
            error_type="AdapterProcessError",
            message=f"Adapter worker returned invalid JSON: {exc}",
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
        )
    report.setdefault("adapter", name)
    report["timeoutSeconds"] = timeout_seconds
    return report


def _adapter_process_error_report(
    name: str,
    adapter_factory,
    *,
    error_type: str,
    message: str,
    dry_run: bool,
    timeout_seconds: int,
) -> dict:
    adapter = None
    try:
        adapter = adapter_factory()
    except Exception:
        pass
    return {
        "status": "error",
        "adapter": name,
        "universityId": getattr(
            adapter,
            "university_id",
            getattr(adapter_factory, "university_id", None),
        ),
        "sourceUrl": getattr(
            adapter,
            "catalog_url",
            getattr(adapter_factory, "catalog_url", None),
        ),
        "errorType": error_type,
        "message": message,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "dryRun": dry_run,
        "timeoutSeconds": timeout_seconds,
    }


def _dedicated_adapter_timeout_seconds() -> int:
    value = os.environ.get("GRADWINDOW_ADAPTER_TIMEOUT_SECONDS", "")
    try:
        return max(1, int(value)) if value else DEDICATED_ADAPTER_TIMEOUT_SECONDS
    except ValueError:
        return DEDICATED_ADAPTER_TIMEOUT_SECONDS


def _print_pipeline_progress(phase: str, status: str, **details) -> None:
    print(
        json.dumps(
            {"pipelineProgress": {"phase": phase, "status": status, **details}},
            ensure_ascii=False,
        ),
        flush=True,
    )


def _source_monitor_progress(completed: int, total: int) -> None:
    if completed == 1 or completed == total or completed % 25 == 0:
        _print_pipeline_progress(
            "application-source-monitor",
            "running",
            completed=completed,
            total=total,
        )


def _approve_all_programmes(*, reviewer: str, parsed_only: bool) -> dict:
    report = {}
    for university_id in _pending_programme_candidate_university_ids():
        report[university_id] = approve_programme_candidates(
            university_id=university_id,
            reviewer=reviewer,
            parsed_only=parsed_only,
        )
    return report


def _auto_approve_programmes(
    university_ids: set[str],
    *,
    reviewer: str,
) -> dict:
    report = {}
    for university_id in sorted(university_ids):
        try:
            report[university_id] = approve_programme_candidates(
                university_id=university_id,
                reviewer=reviewer,
                parsed_only=False,
            )
        except Exception as exc:
            report[university_id] = {
                "status": "error",
                "errorType": type(exc).__name__,
                "message": str(exc),
            }
    return report


def _pending_programme_candidate_university_ids() -> list[str]:
    candidates = read_json(PROGRAMME_CANDIDATES_PATH, {"items": []})
    return sorted(
        {
            item["universityId"]
            for item in candidates.get("items", [])
            if item.get("type") == "new-programme"
            and item.get("status", "pending") == "pending"
            and item.get("universityId")
        }
    )


def _university_by_id(university_id: str) -> dict:
    universities = read_json(UNIVERSITIES_PATH).get("universities", [])
    for university in universities:
        if university.get("id") == university_id:
            return university
    raise SystemExit(f"Unknown university id: {university_id}")


def _generic_prefix(university_id: str) -> str:
    ignored = {"the", "university", "of", "and", "college", "institute"}
    parts = [part for part in university_id.split("-") if part not in ignored]
    return "-".join(parts[:3]) if parts else university_id.split("-", 1)[0]


if __name__ == "__main__":
    main()
