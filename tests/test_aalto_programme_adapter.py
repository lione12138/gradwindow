from __future__ import annotations

import json

from gradwindow.programme_adapters.aalto import AaltoAdapter

STUDIES_API = "https://www.aalto.fi/aalto_api/studies/list"

STUDIES_PAYLOAD = json.dumps(
    {
        "data": [
            {
                "id": "30196",
                "name": "Life Science Technologies, Master of Science (Technology)",
                "degree": "Master of Science (Technology)",
                "degreeType": "masters",
                "url": "/en/study-options/life-science-technologies-master-of-science-technology",
            },
            {
                "id": "33385",
                "name": "Visual Cultures, Curating and Contemporary Art, Master of Arts (Art and Design)",
                "degree": "Master of Arts (Art and Design)",
                "degreeType": "masters",
                "url": "/en/study-options/visual-cultures-curating-and-contemporary-art-master-of-arts-art-and-design",
            },
            {
                "id": "15521",
                "name": "International Business, Bachelor of Science and Master of Science",
                "degree": "Bachelor of Science + Master of Science",
                "degreeType": "bachelors",
                "url": "/en/study-options/international-business-bachelor-of-science-and-master-of-science-economics-and-business",
            },
        ]
    }
)


def test_aalto_uses_the_official_studies_api_and_keeps_only_masters() -> None:
    calls = []

    def fetcher(url: str) -> str:
        calls.append(url)
        return STUDIES_PAYLOAD

    adapter = AaltoAdapter()
    adapter.minimum_expected_programmes = 2
    catalog = adapter.parse_catalog_from_fetcher(fetcher)

    assert calls == [STUDIES_API]
    assert [programme.id for programme in catalog.programmes] == [
        "aalto-life-science-technologies-msc",
        "aalto-visual-cultures-curating-and-contemporary-art-ma",
    ]
    assert [programme.degree_type for programme in catalog.programmes] == ["MSc", "MA"]
    assert all(programme.windows == [] for programme in catalog.programmes)
    assert catalog.diagnostics == {
        "apiStudyOptions": 3,
        "apiMasterOptions": 2,
    }


def test_aalto_rejects_an_api_response_without_a_data_list() -> None:
    adapter = AaltoAdapter()
    adapter.minimum_expected_programmes = 1

    try:
        adapter.parse_catalog('{"data": {}}')
    except ValueError as exc:
        assert "data list" in str(exc)
    else:
        raise AssertionError("invalid Aalto API payload should fail discovery")
