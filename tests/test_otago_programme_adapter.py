from __future__ import annotations

import json

import pytest

from gradwindow.programme_adapters.otago import OtagoAdapter
from gradwindow.programme_discovery import discover_programmes


def test_otago_records_the_cloudflare_catalogue_limitation() -> None:
    html = "<title>Home - AskOtago Service Portal</title><h1>AskOtago</h1>"
    row = OtagoAdapter().parse_catalog(html).programmes[0]
    assert row.id == "otago-masters-programmes"
    assert row.parse_status == "no-deadline"
    assert "Cloudflare" in row.deadline_text
    assert row.windows == []


def test_otago_rejects_an_unrecognised_heartbeat_page() -> None:
    with pytest.raises(ValueError, match="AskOtago"):
        OtagoAdapter().parse_catalog("<title>Unexpected page</title>")


def test_otago_machine_readable_report_marks_catalogue_blocked(tmp_path) -> None:
    programs_path = tmp_path / "programs.json"
    candidates_path = tmp_path / "programme-candidates.json"
    state_path = tmp_path / "programme-catalog-state.json"
    programs_path.write_text(
        json.dumps(
            {
                "programs": [
                    {
                        "id": "otago-masters-programmes",
                        "universityId": "university-of-otago",
                        "name": "Masters programmes",
                        "degreeType": "Master",
                        "faculty": "Masters study",
                        "applicationUrl": OtagoAdapter.application_url,
                        "sourceUrl": "https://www.otago.ac.nz/study/masters",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    report = discover_programmes(
        OtagoAdapter(),
        programs_path=programs_path,
        candidates_path=candidates_path,
        state_path=state_path,
        fetcher=lambda url: "<title>Home - AskOtago Service Portal</title>",
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))["universities"][
        "university-of-otago"
    ]
    assert report["catalogueStatus"] == "blocked"
    assert state["catalogueStatus"] == "blocked"
    assert "Cloudflare" in report["limitationReason"]
