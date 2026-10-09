import json

import pytest

from gradwindow.programme_adapters.indiana_bloomington import _programmes


def payload():
    master = dict(
        name="Economics",
        degree="Master of Science",
        diploma_badge="Master's",
        campus="IU Bloomington",
        url="https://academics.iu.edu/degrees/bloomington/master-of-science/economics.html",
    )
    return dict(
        status=200,
        pagination=dict(page=1, pages=1, total=3, thisPage=3, next=None, prev=None),
        data=[master, dict(master), dict(master, diploma_badge="Doctoral")],
    )


def test_complete_api_deduplicates_and_excludes_doctoral_records():
    rows = _programmes(json.dumps(payload()))
    assert len(rows) == 1
    assert rows[0].name == "Economics"
    assert not rows[0].windows


@pytest.mark.parametrize(
    "changes",
    [
        {"pages": 2},
        {"page": 2},
        {"total": 4},
        {"thisPage": 2},
        {"next": "page2"},
        {"prev": "page1"},
    ],
)
def test_partial_api_response_fails_even_if_count_would_pass(changes):
    data = payload()
    data["pagination"].update(changes)
    with pytest.raises(ValueError, match="incomplete"):
        _programmes(json.dumps(data))


@pytest.mark.parametrize("field", ["name", "degree", "url"])
def test_incomplete_master_record_is_not_silently_omitted(field):
    data = payload()
    data["data"][0][field] = ""
    with pytest.raises(ValueError, match="missing"):
        _programmes(json.dumps(data))


def test_duplicate_url_cannot_hide_changed_identity():
    data = payload()
    data["data"][1]["degree"] = "Master of Arts"
    with pytest.raises(ValueError, match="conflicting"):
        _programmes(json.dumps(data))
