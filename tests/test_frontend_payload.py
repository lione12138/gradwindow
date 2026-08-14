from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from gradwindow.frontend import build_frontend_payloads

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_payload_is_compact_complete_and_trust_preserving() -> None:
    frontend, closed, details = build_frontend_payloads(date(2026, 8, 14))
    initial_rows = frontend["records"]["rows"]
    closed_rows = closed["records"]["rows"]

    assert len(initial_rows) + len(closed_rows) == (
        frontend["meta"]["officialCount"]
        + frontend["meta"]["predictionCount"]
        + frontend["meta"]["recurringCount"]
    )
    assert len(closed_rows) == frontend["meta"]["statusCounts"]["closed"]
    assert (
        len(json.dumps(frontend, ensure_ascii=False, separators=(",", ":")).encode())
        < 2_500_000
    )
    assert frontend["rankings"]["rankings"]["the"]["available"] is True
    assert frontend["rankings"]["rankings"]["arwu"]["available"] is True
    assert frontend["rankings"]["rankings"]["usnews"]["available"] is False
    assert frontend["rankings"]["rankings"]["usnews"]["rows"] == []
    assert details
    assert any(
        item.get("evidence")
        for payload in details.values()
        for item in payload["records"]
    )

    dictionaries = frontend["records"]["dictionaries"]
    sample = initial_rows[0]
    assert dictionaries["urls"][sample[8]].startswith("http")
    assert dictionaries["urls"][sample[9]].startswith("http")


def test_frontend_decoder_restores_record_fields() -> None:
    node = shutil.which("node")
    assert node is not None, "Node.js is required for frontend payload tests"
    module_uri = (ROOT / "web" / "frontend-data.js").resolve().as_uri()
    script = f"""
      import {{ decodeRecordBundle }} from {json.dumps(module_uri)};
      const universities = [{{
        id: "test-university", school: "Test University", qsRank: 9,
        country: "Testland", region: "Europe"
      }}];
      const bundle = {{
        dictionaries: {{
          scopes: [["test-program", "programme", "Test MSc"]],
          intakes: [["Fall 2027", {{ cycleYear: 2027, term: "fall" }}]],
          rounds: ["Round 1"], categorySets: [["all"]],
          urls: ["https://apply.example", "https://source.example"],
          statuses: ["official"], sourceCycles: [], confidences: [],
          monitors: [{{ status: "ok" }}]
        }},
        rows: [["window-1", 0, 0, 0, 0, 0, "2026-09-01", "2026-12-01", 0, 1, "2026-08-14", null, 0, -1, -1, null, 0]]
      }};
      console.log(JSON.stringify(decodeRecordBundle(bundle, universities)[0]));
    """
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    record = json.loads(result.stdout)
    assert record["id"] == "window-1"
    assert record["universityId"] == "test-university"
    assert record["program"] == "Test MSc"
    assert record["applicationUrl"] == "https://apply.example"
    assert record["sourceUrl"] == "https://source.example"
    assert record["sourceMonitor"] == {"status": "ok"}
