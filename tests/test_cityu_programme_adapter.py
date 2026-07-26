import pytest

from gradwindow.programme_adapters.cityu import CityUAdapter

HTML = """<table><caption><strong>Department of Computing</strong></caption><tr><td>P62</td><td><a href="https://www.cityu.edu.hk/en/pg/programme/p62">MSc Computer Science<br/>電腦科學</a></td><td><div app_start_date="2025/09/16 10:00:00" app_deadline="2026/03/31 23:59:00" app_deadline_nl="2026/02/28 23:59:00"></div></td></tr></table>"""


def test_cityu_parses_official_local_and_nonlocal_windows() -> None:
    catalog = CityUAdapter(minimum_expected_programmes=1).parse_catalog(HTML)
    programme = catalog.programmes[0]
    assert programme.id == "cityu-computer-science-msc"
    assert programme.name == "MSc Computer Science"
    assert [
        (window.opens_at, window.closes_at, window.applicant_categories)
        for window in programme.windows
    ] == [
        ("2025-09-16", "2026-03-31", ["domestic-students"]),
        ("2025-09-16", "2026-02-28", ["international-students"]),
    ]


def test_cityu_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 2"):
        CityUAdapter(minimum_expected_programmes=2).parse_catalog(HTML)
