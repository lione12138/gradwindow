from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from gradwindow.frontend import build_frontend_payloads
from gradwindow.io import read_json
from gradwindow.paths import APPLICATIONS_PATH

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_payload_is_compact_complete_and_trust_preserving() -> None:
    quarantined_id = read_json(APPLICATIONS_PATH)["applications"][0]["id"]
    frontend, closed, details = build_frontend_payloads(
        date(2026, 8, 14),
        published_audit={
            "recordTrustStatuses": {quarantined_id: "needs-review"},
        },
    )
    initial_rows = frontend["records"]["rows"]
    closed_rows = closed["records"]["rows"]

    assert len(initial_rows) + len(closed_rows) == (
        frontend["meta"]["officialCount"]
        + frontend["meta"]["predictionCount"]
        + frontend["meta"]["recurringCount"]
    )
    trust_dictionary = closed["records"]["dictionaries"]["trustStatuses"]
    trusted_closed_rows = sum(
        trust_dictionary[row[18]] == "current" for row in closed_rows
    )
    assert trusted_closed_rows == frontend["meta"]["statusCounts"]["closed"]
    assert (
        len(json.dumps(frontend, ensure_ascii=False, separators=(",", ":")).encode())
        < 2_500_000
    )
    assert frontend["rankings"]["rankings"]["the"]["available"] is True
    assert frontend["rankings"]["rankings"]["arwu"]["available"] is True
    assert frontend["rankings"]["rankings"]["usnews"]["available"] is False
    assert frontend["rankings"]["rankings"]["usnews"]["rows"] == []
    adapter_health = frontend["meta"]["adapterHealth"]
    assert adapter_health["updatedAt"]
    assert adapter_health["summary"]["totalAdapters"] == 302
    assert 0 <= adapter_health["summary"]["healthyAdapters"] <= 302
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
    quarantine_bundle = next(
        bundle
        for bundle in (frontend["records"], closed["records"])
        if any(row[0] == quarantined_id for row in bundle["rows"])
    )
    quarantined_row = next(
        row for row in quarantine_bundle["rows"] if row[0] == quarantined_id
    )
    assert (
        quarantine_bundle["dictionaries"]["trustStatuses"][quarantined_row[18]]
        == "needs-review"
    )
    assert frontend["meta"]["trustStatusCounts"]["needs-review"] == 1
    assert frontend["meta"]["trustedOfficialCount"] == (
        frontend["meta"]["officialCount"] - 1
    )


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
          monitors: [{{ status: "ok" }}], deadlineSemantics: ["before"]
          , trustStatuses: ["needs-review"]
        }},
        rows: [["window-1", 0, 0, 0, 0, 0, "2026-09-01", "2026-12-01", 0, 1, "2026-08-14", null, 0, -1, -1, null, 0, 0, 0]]
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
    assert record["deadlineSemantics"] == "before"
    assert record["trustStatus"] == "needs-review"
