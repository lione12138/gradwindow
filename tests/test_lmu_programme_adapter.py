import pytest

from gradwindow.programme_adapters.lmu import LMUAdapter

CATALOGUE = """
<div class="c-link-list--default">
  <h2>English-taught master's degree programs</h2>
  <ul>
    <li><a href="https://www.en.master.econ.uni-muenchen.de/">Economics</a></li>
    <li><a href="https://www.statistik.uni-muenchen.de/master/">Statistics and Data Science</a></li>
  </ul>
</div>
<div class="c-link-list--default">
  <h2>Double degree programs</h2>
  <ul><li><a href="https://partner.example/program">External programme</a></li></ul>
</div>
"""


def test_lmu_adapter_discovers_english_taught_masters() -> None:
    catalog = LMUAdapter(minimum_expected_programmes=2).parse_catalog(CATALOGUE)

    assert [item.name for item in catalog.programmes] == [
        "MSc Statistics and Data Science",
        "Master's Programme in Economics",
    ]
    assert catalog.programmes[0].id == "lmu-statistics-data-science-msc"
    assert all(item.windows == [] for item in catalog.programmes)


def test_lmu_adapter_rejects_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        LMUAdapter(minimum_expected_programmes=3).parse_catalog(CATALOGUE)
