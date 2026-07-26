import json

import pytest

from gradwindow.programme_adapters.ku_leuven import KULeuvenAdapter

PAYLOAD = {
    "hits": {
        "total": {"value": 3, "relation": "eq"},
        "hits": [
            {
                "_source": {
                    "id": "50269035",
                    "institution": "50000050",
                    "qualificationId": "50269035",
                    "enQualificationDegreeLevel": "Master's",
                    "applyUrl": "https://www.kuleuven.be/english/apply",
                    "qualificationLanguageSet": [
                        {
                            "qualificationTitleSet": [
                                {
                                    "qualificationLangu": "NL",
                                    "description": "Master in de wijsbegeerte (Leuven)",
                                }
                            ]
                        },
                        {
                            "qualificationTitleSet": [
                                {
                                    "qualificationLangu": "EN",
                                    "description": "Master of Philosophy (Leuven)",
                                }
                            ]
                        },
                    ],
                }
            },
            {
                "_source": {
                    "id": "53597572",
                    "institution": "50000050",
                    "qualificationId": "53597572",
                    "enQualificationDegreeLevel": "Advanced Master's",
                    "applyUrl": "https://www.kuleuven.be/english/apply",
                    "qualificationLanguageSet": [
                        {
                            "qualificationTitleSet": [
                                {
                                    "qualificationLangu": "EN",
                                    "description": "Master of Bioethics (Leuven)",
                                }
                            ]
                        }
                    ],
                }
            },
            {
                "_source": {
                    "id": "wrong-institution",
                    "institution": "50000051",
                    "qualificationId": "wrong-institution",
                    "enQualificationDegreeLevel": "Master's",
                    "qualificationLanguageSet": [],
                }
            },
        ],
    }
}


def test_ku_leuven_adapter_parses_official_search_results() -> None:
    catalog = KULeuvenAdapter(minimum_expected_programmes=2).parse_json(
        json.dumps(PAYLOAD)
    )

    assert [item.name for item in catalog.programmes] == [
        "Master of Bioethics (Leuven)",
        "Master of Philosophy (Leuven)",
    ]
    assert catalog.programmes[0].degree_type == "Advanced Master's"
    assert catalog.programmes[1].source_url.endswith("/e/CQ_50269035")
    assert all(item.windows == [] for item in catalog.programmes)


def test_ku_leuven_adapter_rejects_truncated_results() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        KULeuvenAdapter(minimum_expected_programmes=3).parse_json(json.dumps(PAYLOAD))
