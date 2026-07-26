import pytest

from gradwindow.programme_adapters.kyoto import KyotoAdapter

CATALOGUE = """
<h2><a id="undergraduate-program"></a>Undergraduate program</h2>
<h3>Engineering</h3>
<h4><a href="https://www.iup.kyoto-u.ac.jp/">Undergraduate International Course</a></h4>
<table><tr><th>Degree</th></tr><tr><td>Bachelor's</td></tr></table>
<h2><a id="graduate-programs"></a>Graduate programs</h2>
<h3>Letters</h3>
<h4><a href="https://www.cats.bun.kyoto-u.ac.jp/jdts/">Joint Degree Master of Arts Program in Transcultural Studies (JDTS)</a></h4>
<table><tr><th>Degree</th><th>Enrollment date</th></tr><tr><td>Master's</td><td>October</td></tr></table>
<h3>Management</h3>
<h4><a href="https://www.gsm.kyoto-u.ac.jp/en/education/mba/">International MBA (i-MBA)</a></h4>
<table><tr><th>Degree</th><th>Enrollment date</th></tr><tr><td>Master's</td><td>April</td></tr></table>
"""


def test_kyoto_adapter_discovers_english_taught_masters() -> None:
    catalog = KyotoAdapter(minimum_expected_programmes=2).parse_catalog(CATALOGUE)

    assert [item.name for item in catalog.programmes] == [
        "International MBA (i-MBA)",
        "Joint Degree Master of Arts Program in Transcultural Studies (JDTS)",
    ]
    assert catalog.programmes[0].faculty == "Management"
    assert all(item.windows == [] for item in catalog.programmes)


def test_kyoto_adapter_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        KyotoAdapter(minimum_expected_programmes=3).parse_catalog(CATALOGUE)
