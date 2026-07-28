import pytest

from gradwindow.programme_adapters.nottingham import NottinghamAdapter

PAGE = """
<a href="/pgstudy/course/taught/accounting-and-finance-msc"><span>Accounting and Finance MSc</span></a>
<a href="/pgstudy/course/taught/applied-linguistics-ma"><span>Applied Linguistics MA</span></a>
<a href="/pgstudy/course/research/american-studies-phd"><span>American Studies PhD</span></a>
"""


def test_nottingham_adapter_keeps_taught_masters_and_deduplicates_pages() -> None:
    catalog = NottinghamAdapter(minimum_expected_programmes=2).parse_pages([PAGE, PAGE])

    assert [item.name for item in catalog.programmes] == [
        "Accounting and Finance MSc",
        "Applied Linguistics MA",
    ]
    assert all("/taught/" in item.source_url for item in catalog.programmes)


def test_nottingham_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        NottinghamAdapter(minimum_expected_programmes=3).parse_pages([PAGE])
