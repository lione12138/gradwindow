import json

import pytest

from gradwindow.http_client import FetchFailure
from gradwindow.programme_adapters.uva import API_URL, APPLICATION_URL, UvAAdapter

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


def test_uva_missing_guide_preserves_catalogue_with_warning():
    def fetcher(url):
        if url == APPLICATION_URL:
            raise FetchFailure("HTTP 404", kind="http", status_code=404)
        assert url == API_URL
        return json.dumps(ITEMS)

    catalog = UvAAdapter(2).parse_catalog_from_fetcher(fetcher)
    assert len(catalog.programmes) == 2
    assert catalog.warnings[0]["reason"] == "APPLICATION_GUIDE_UNAVAILABLE"
    assert all(p.application_url == p.source_url for p in catalog.programmes)
    assert all(not p.windows for p in catalog.programmes)


def test_uva_catalogue_failure_is_not_suppressed():
    def fetcher(url):
        raise FetchFailure("HTTP 503", kind="http", status_code=503)

    with pytest.raises(FetchFailure):
        UvAAdapter(2).parse_catalog_from_fetcher(fetcher)


@pytest.mark.parametrize(
    "guide,warning",
    [("Every programme has its own requirements", False), ("Access denied", True)],
)
def test_uva_guide_validation_remains_explicit(guide, warning):
    pages = {API_URL: json.dumps(ITEMS), APPLICATION_URL: guide}
    catalog = UvAAdapter(2).parse_catalog_from_fetcher(pages.__getitem__)
    assert bool(catalog.warnings) is warning
    assert all(not p.windows for p in catalog.programmes)
