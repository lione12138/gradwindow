from __future__ import annotations

import pytest

from gradwindow.io import read_json, write_json
from gradwindow.programme_adapters.base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)
from gradwindow.programme_discovery import discover_programmes


class PartialDedicatedAdapter(BaseProgrammeAdapter):
    university_id = "example-university"
    catalog_url = "https://example.edu/programmes"
    intake = "September 2027"
    replace_pending_candidates = True

    def __init__(self, diagnostics=None, *, include_windows=True):
        self.diagnostics = diagnostics or {}
        self.include_windows = include_windows

    def parse_catalog(self, _html):
        programmes = []
        for name in ("new", "known", "guidance"):
            windows = []
            if self.include_windows:
                windows.append(
                    DiscoveredWindow(
                        round="Main",
                        opens_at=None if name == "guidance" else "2026-10-01",
                        closes_at="2027-06-30",
                        intake=self.intake,
                        opens_at_basis="official" if name != "guidance" else "missing",
                    )
                )
            programmes.append(
                DiscoveredProgramme(
                    id=f"example-{name}-msc",
                    name=f"{name.title()} MSc",
                    degree_type="MSc",
                    faculty="Example faculty",
                    department="",
                    source_url=f"https://example.edu/programmes/{name}",
                    application_url=f"https://example.edu/programmes/{name}#apply",
                    windows=windows,
                    deadline_text="Synthetic official application date fixture.",
                    parse_status="parsed" if windows else "no-deadline",
                )
            )
        return DiscoveredCatalog(None, programmes, diagnostics=self.diagnostics)


def discover(tmp_path, adapter):
    return discover_programmes(
        adapter,
        programs_path=tmp_path / "programs.json",
        applications_path=tmp_path / "applications.json",
        candidates_path=tmp_path / "programme-candidates.json",
        window_candidates_path=tmp_path / "window-candidates.json",
        state_path=tmp_path / "programme-catalog-state.json",
        fetcher=lambda _url: "<html></html>",
    )


def seed_candidates(tmp_path):
    write_json(
        tmp_path / "programs.json",
        {
            "programs": [
                {
                    "id": f"example-{name}-msc",
                    "universityId": "example-university",
                    "applicationUrl": f"https://example.edu/programmes/{name}#apply",
                }
                for name in ("known", "guidance")
            ]
        },
    )
    discover(tmp_path, PartialDedicatedAdapter())
    for filename in ("programme-candidates.json", "window-candidates.json"):
        payload = read_json(tmp_path / filename)
        for item in payload["items"]:
            item["detectedAt"] = "2026-10-10T00:00:00+00:00"
            item["reviewNotes"] = "Keep the earlier source review."
            if "record" in item:
                item["record"]["verifiedAt"] = "2026-10-10"
                item["confirmation"].update(
                    observationCount=2,
                    firstObservedAt="2026-10-10T00:00:00+00:00",
                    lastObservedAt="2026-10-11T00:00:00+00:00",
                )
        write_json(tmp_path / filename, payload)


@pytest.mark.parametrize(
    "diagnostic", ["detailUnvisitedProgrammeIds", "detailFailedProgrammeIds"]
)
@pytest.mark.parametrize("include_windows", [False, True])
def test_replacing_adapter_keeps_deferred_candidates_without_reverification(
    tmp_path, diagnostic, include_windows
):
    seed_candidates(tmp_path)
    programme_path = tmp_path / "programme-candidates.json"
    window_path = tmp_path / "window-candidates.json"
    before_programmes = read_json(programme_path)
    before_windows = read_json(window_path)
    assert len(before_programmes["items"]) == 2
    assert len(before_windows["items"]) == 1

    report = discover(
        tmp_path,
        PartialDedicatedAdapter(
            {
                diagnostic: [
                    "example-new-msc",
                    "example-known-msc",
                    "example-guidance-msc",
                ]
            },
            include_windows=include_windows,
        ),
    )

    assert read_json(programme_path) == before_programmes
    assert read_json(window_path) == before_windows
    assert report["newCandidates"] == 0
    assert report["newGuidanceCandidates"] == 0
    assert report["newWindowCandidates"] == 0
    assert report["pendingWindowCandidates"] == 1


def test_replacement_only_preserves_deferred_scopes_and_reviewed_records(tmp_path):
    seed_candidates(tmp_path)
    programme_path = tmp_path / "programme-candidates.json"
    window_path = tmp_path / "window-candidates.json"
    programme_payload = read_json(programme_path)
    deferred = next(
        item for item in programme_payload["items"] if item["type"] == "new-programme"
    )
    reviewed = {
        **deferred,
        "id": "new-programme:example-reviewed-msc",
        "programme": {**deferred["programme"], "id": "example-reviewed-msc"},
        "status": "rejected",
        "reviewedAt": "2026-10-11",
        "reviewedBy": "Test reviewer",
    }
    obsolete = {
        **deferred,
        "id": "new-programme:example-obsolete-msc",
        "programme": {**deferred["programme"], "id": "example-obsolete-msc"},
    }
    programme_payload["items"].extend([reviewed, obsolete])
    write_json(programme_path, programme_payload)
    window_payload = read_json(window_path)
    reviewed_window = {
        **window_payload["items"][0],
        "id": "adapter-window:example-reviewed-window",
        "status": "approved",
        "reviewedAt": "2026-10-11",
        "reviewedBy": "Test reviewer",
    }
    window_payload["items"].append(reviewed_window)
    write_json(window_path, window_payload)

    discover(
        tmp_path,
        PartialDedicatedAdapter(
            {"detailUnvisitedProgrammeIds": ["example-new-msc"]},
            include_windows=False,
        ),
    )

    after_programmes = {item["id"]: item for item in read_json(programme_path)["items"]}
    assert after_programmes == {deferred["id"]: deferred, reviewed["id"]: reviewed}
    assert read_json(window_path)["items"] == [reviewed_window]
