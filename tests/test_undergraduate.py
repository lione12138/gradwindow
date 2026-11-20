import pytest

from gradwindow.io import write_json
from gradwindow.undergraduate import load_undergraduate_windows


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"applicantScope": "domestic"}, "applicantScope"),
        ({"eligibilitySourceUrl": "https://example.com/eligible"}, "eligibility"),
        ({"sourceUrl": "https://www.ucas.com/"}, "university deadline"),
        ({"openingSourceUrl": "https://example.com/open"}, "official opening"),
        ({"opensAt": "2028-01-01"}, "opensAt is after closesAt"),
    ],
)
def test_undergraduate_feed_rejects_unpublishable_windows(tmp_path, changes, message):
    path = tmp_path / "undergraduate.json"
    record = load_undergraduate_windows()[0]
    for key in ("school", "schoolZh", "country", "region", "qsRank", "rankDisplay"):
        record.pop(key)
    write_json(path, [{**record, **changes}])

    with pytest.raises(ValueError, match=message):
        load_undergraduate_windows(path)


def test_undergraduate_feed_uses_canonical_university_metadata():
    records = load_undergraduate_windows()
    ucl = next(
        record
        for record in records
        if record["universityId"] == "ucl-university-college-london"
    )
    assert ucl["schoolZh"] == "伦敦大学学院"
    assert ucl["qsRank"] > 0
    assert ucl["applicantScope"] in {"international", "international-and-domestic"}
