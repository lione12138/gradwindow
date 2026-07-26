import json

import pytest

from gradwindow.programme_adapters.uva import UvAAdapter

ITEMS = {
    "items": [
        {
            "title": "Computer Science (joint degree UvA/VU)",
            "url": "https://www.uva.nl/en/programmes/computer-science.html?origin=x",
            "studyType": "master",
            "studytitle": ["msc"],
            "faculty": ["faculty-of-science"],
        },
        {
            "title": "History",
            "url": "https://www.uva.nl/en/programmes/history.html",
            "studyType": "master",
            "studytitle": ["ma"],
            "faculty": ["humanities"],
        },
    ]
}


def test_uva_parses_official_master_json_and_reuses_computer_science_id() -> None:
    catalog = UvAAdapter(minimum_expected_programmes=2).parse_json(json.dumps(ITEMS))
    assert {item.id for item in catalog.programmes} == {
        "uva-vu-computer-science-msc",
        "uva-history-master",
    }
    assert all(item.windows == [] for item in catalog.programmes)


def test_uva_rejects_truncated_json() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        UvAAdapter(minimum_expected_programmes=3).parse_json(json.dumps(ITEMS))
