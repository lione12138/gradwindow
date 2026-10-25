from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import quote

import pytest

_SCRIPT = Path("scripts/collect_pipeline_diagnostics.py")
_SPEC = importlib.util.spec_from_file_location("pipeline_diagnostics", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
diagnostics = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diagnostics)


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_failed_pipeline_retains_only_allowlisted_sanitized_snapshots(tmp_path):
    root = tmp_path / "repo"
    secret = 'private/token+"value'
    manifest = "data/ops/programme-candidates.json"
    shard = "data/ops/programme-candidates/by-university/example.json"
    ledger = ".cache/pipeline-run/dedicated-discovery.json"
    _write(root, manifest, '{"partitioning": {"files": ["example.json"]}}')
    _write(root, shard, json.dumps({"message": secret, "candidates": []}))
    _write(root, ledger, '{"status": "running"}')
    for private in (
        ".env",
        ".cache/browser-fetch/cache.db",
        "data/ops/private.json",
        "data/applications.json",
        "subscriptions/.dev.vars",
        "data/ops/programme-candidates/by-university/credentials.txt",
    ):
        _write(root, private, secret)
    raw_log = _write(tmp_path, "raw.log", f"failure {secret} {quote(secret, safe='')}")
    output = tmp_path / "artifact"

    result = diagnostics.collect_diagnostics(
        root,
        output,
        log_path=raw_log,
        outcome="failure",
        environment={"DEEPSEEK_API_KEY": secret},
    )

    assert result["pipelineOutcome"] == "failure"
    assert result["publicationSafe"] is False
    assert {entry["path"] for entry in result["files"]} == {
        "pipeline.log",
        manifest,
        shard,
        ledger,
    }
    assert json.loads((output / shard).read_text())["message"] == "[REDACTED]"
    assert (output / "pipeline.log").read_text() == "failure [REDACTED] [REDACTED]"
    assert (
        "never restored or published automatically"
        in (output / "summary.md").read_text()
    )
    assert raw_log.read_text() == f"failure {secret} {quote(secret, safe='')}"


def test_collector_reports_limits_without_truncating_json(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    _write(root, diagnostics.FILES[0], '{"complete": true}')
    _write(root, diagnostics.FILES[1], " " * 101)
    _write(root, diagnostics.FILES[2], '{"complete": true}')
    raw_log = _write(tmp_path, "raw.log", "0123456789")
    monkeypatch.setattr(diagnostics, "MAX_LOG_BYTES", 5)
    monkeypatch.setattr(diagnostics, "MAX_FILE_BYTES", 100)

    result = diagnostics.collect_diagnostics(
        root,
        tmp_path / "artifact",
        log_path=raw_log,
        outcome="failure",
        environment={},
        max_total_bytes=25,
    )

    assert result["logTruncated"] is True
    assert (tmp_path / "artifact/pipeline.log").read_text() == "56789"
    assert result["skipped"] == [
        {"path": diagnostics.FILES[1], "reason": "file-size-limit"},
        {"path": diagnostics.FILES[2], "reason": "total-size-limit"},
    ]
    assert json.loads((tmp_path / "artifact" / diagnostics.FILES[0]).read_text())


def test_collector_refuses_existing_staging_directory(tmp_path):
    output = tmp_path / "artifact"
    output.mkdir()
    _write(output, "unsafe-old-file", "secret")

    with pytest.raises(FileExistsError):
        diagnostics.collect_diagnostics(
            tmp_path,
            output,
            log_path=tmp_path / "missing.log",
            outcome="failure",
            environment={},
        )


def test_collector_rejects_symlink_in_allowlist(tmp_path):
    root = tmp_path / "repo"
    link = root / diagnostics.FILES[0]
    link.parent.mkdir(parents=True)
    private = _write(tmp_path, "private.json", "private content")
    try:
        link.symlink_to(private)
    except OSError:
        pytest.skip("Creating symlinks requires elevated privileges on this host")

    result = diagnostics.collect_diagnostics(
        root,
        tmp_path / "artifact",
        log_path=tmp_path / "missing.log",
        outcome="failure",
        environment={},
    )

    assert result["skipped"] == [
        {"path": diagnostics.FILES[0], "reason": "unsafe-path"}
    ]
    assert result["files"] == []
