"""Retain bounded, sanitized pipeline diagnostics without publishing failed data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote

FILES = (
    ".cache/pipeline-run/dedicated-discovery.json",
    "data/ops/programme-candidates.json",
    "data/ops/window-candidates.json",
    "data/ops/programme-catalog-state.json",
    "data/ops/programme-adapter-health.json",
    "data/ops/monitor-state.json",
    "data/ops/application-source-state.json",
    "data/ops/monitor-report.json",
    "data/ops/review-queue.json",
    "data/ops/reports/programme-adapter-health.md",
    "data/ops/reports/generic-programme-discovery-report.json",
    "data/ops/reports/generic-seed-discovery-report.json",
    "data/ops/reports/published-data-audit.json",
)
SHARD_DIRECTORIES = (
    "data/ops/programme-candidates/by-university",
    "data/ops/window-candidates/by-university",
    "data/ops/programme-catalog-state/by-university",
)
SECRET_NAMES = (
    "SERPER_SEARCH_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_BROWSER_API_TOKEN",
    "DEEPSEEK_API_KEY",
)
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_LOG_BYTES = 2 * 1024 * 1024


def _redact(text: str, environment: Mapping[str, str]) -> str:
    variants = set()
    for name in SECRET_NAMES:
        if value := environment.get(name):
            variants.update((value, quote(value, safe=""), json.dumps(value)[1:-1]))
    for value in sorted(variants, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    return text


def _safe_file(path: Path, root: Path) -> bool:
    # Never follow links into credentials, browser caches, or outside the checkout.
    return (
        path.is_file()
        and root in path.resolve().parents
        and not any(part.is_symlink() for part in (path, *path.parents))
    )


def collect_diagnostics(
    root: Path,
    output: Path,
    *,
    log_path: Path,
    outcome: str,
    environment: Mapping[str, str],
    max_total_bytes: int = MAX_TOTAL_BYTES,
) -> dict:
    root = root.resolve()
    # A fresh directory prevents an older/raw artifact from entering this run.
    output.mkdir(parents=True, exist_ok=False)
    inventory: dict = {
        "pipelineOutcome": outcome,
        "publicationSafe": False,
        "purpose": "Manual diagnosis/recovery only; not an automatic restore source.",
        "files": [],
        "missing": [],
        "skipped": [],
    }
    total_bytes = 0

    def retain(relative: str, text: str) -> None:
        nonlocal total_bytes
        content = _redact(text, environment).encode("utf-8")
        if total_bytes + len(content) > max_total_bytes:
            inventory["skipped"].append(
                {"path": relative, "reason": "total-size-limit"}
            )
            return
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        total_bytes += len(content)
        inventory["files"].append(
            {
                "path": relative,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )

    if log_path.is_file() and not log_path.is_symlink():
        with log_path.open("rb") as handle:
            size = log_path.stat().st_size
            handle.seek(max(0, size - MAX_LOG_BYTES))
            log_text = handle.read(MAX_LOG_BYTES).decode("utf-8", errors="replace")
        inventory["logTruncated"] = size > MAX_LOG_BYTES
        retain("pipeline.log", log_text)
    else:
        inventory["missing"].append("pipeline.log")

    paths = [root / relative for relative in FILES]
    for relative in SHARD_DIRECTORIES:
        directory = root / relative
        if directory.is_dir() and not directory.is_symlink():
            paths.extend(sorted(directory.glob("*.json")))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if not path.exists():
            inventory["missing"].append(relative)
            continue
        if not _safe_file(path, root):
            inventory["skipped"].append({"path": relative, "reason": "unsafe-path"})
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            inventory["skipped"].append({"path": relative, "reason": "file-size-limit"})
            continue
        try:
            retain(relative, path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            inventory["skipped"].append(
                {"path": relative, "reason": type(exc).__name__}
            )
    inventory["retainedBytes"] = total_bytes
    (output / "inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    summary = [
        "### Daily pipeline diagnostics",
        "",
        f"Pipeline outcome: **{outcome}**.",
        f"Retained {len(inventory['files'])} allowlisted files ({total_bytes:,} bytes).",
        f"Missing: {len(inventory['missing'])}; skipped: {len(inventory['skipped'])}.",
        "",
        "Download the `daily-pipeline-diagnostics` artifact for the sanitized log,",
        "per-school progress, candidate/state snapshots, and file inventory.",
        "Files may include unchanged state from checkout; their presence is not proof",
        "of a successful refresh. Retention is 14 days. These snapshots require review",
        "and validation before recovery; they are never restored or published automatically.",
        "",
    ]
    (output / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument(
        "--outcome", choices=("success", "failure", "cancelled"), required=True
    )
    args = parser.parse_args()
    collect_diagnostics(
        args.root,
        args.output,
        log_path=args.log,
        outcome=args.outcome,
        environment=os.environ,
    )


if __name__ == "__main__":
    main()
