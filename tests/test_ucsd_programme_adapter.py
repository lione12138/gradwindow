import pytest

from gradwindow.programme_adapters.ucsd import UCSDAdapter

PAGE = """
<main id="main-content">
  <h4>COMPUTER SCIENCE AND ENGINEERING</h4>
  <ul><li>Computer Science MS, PhD</li><li>Computer Science PhD</li></ul>
  <h4>PUBLIC HEALTH</h4>
  <ul><li>Public Health MPH</li></ul>
</main>
"""


def test_ucsd_adapter_keeps_master_degrees_and_reuses_existing_id() -> None:
    catalog = UCSDAdapter(minimum_expected_programmes=2).parse_catalog(PAGE)

    assert [item.name for item in catalog.programmes] == [
        "Computer Science MS",
        "Public Health MPH",
    ]
    assert catalog.programmes[0].id == "ucsd-computer-science-ms"
    assert catalog.programmes[1].department == "PUBLIC HEALTH"


def test_ucsd_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        UCSDAdapter(minimum_expected_programmes=3).parse_catalog(PAGE)
