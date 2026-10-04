import json

import pytest

from gradwindow.programme_adapters.washington import WashingtonAdapter


@pytest.mark.parametrize(
    "payload", ['{"error": "unavailable"}', '[{"name": "Unknown"}]']
)
def test_rejects_changed_response_schema(payload):
    with pytest.raises(ValueError, match="invalid records|unknown schema"):
        WashingtonAdapter().extract_entries(payload)


def test_rejects_incomplete_catalogue():
    with pytest.raises(ValueError, match="expected at least 225"):
        WashingtonAdapter().parse_catalog("[]")


def test_slate_catalogue_keeps_degree_programmes_only():
    adapter = WashingtonAdapter()
    adapter.minimum_expected_programmes = 1
    rows = [
        {
            "SlateDegreeCode": "MS",
            "SlateProgramDegreeLevel": "Master's",
            "SlateProgramMarketingName": "Data Science (MS)",
            "ProgramURL": "https://www.washington.edu/data-science",
        },
        {
            "SlateDegreeCode": "MSVG",
            "SlateProgramDegreeLevel": "Master's",
            "SlateProgramMarketingName": "Data Science - Visiting Grad",
            "ProgramURL": "https://www.washington.edu/data-science",
        },
        {
            "SlateDegreeCode": "PHD",
            "SlateProgramDegreeLevel": "Doctoral",
            "SlateProgramMarketingName": "Data Science (PhD)",
            "ProgramURL": "https://www.washington.edu/data-science",
        },
    ]
    programmes = adapter.parse_catalog(json.dumps(rows)).programmes
    assert [p.name for p in programmes] == ["Data Science (MS)"]
    assert programmes[0].windows == []


def test_slate_catalogue_rejects_missing_master_source():
    adapter = WashingtonAdapter()
    with pytest.raises(ValueError, match="incomplete master's record"):
        adapter.extract_entries(
            json.dumps(
                [
                    {
                        "SlateDegreeCode": "MS",
                        "SlateProgramDegreeLevel": "Master's",
                        "SlateProgramMarketingName": "Data Science (MS)",
                        "ProgramURL": None,
                    }
                ]
            )
        )
