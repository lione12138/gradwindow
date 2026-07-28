import pytest

from gradwindow.programme_adapters.sorbonne import SorbonneAdapter

PAGE = """
<div class="field-collapse">
  <button class="field-collapse__trigger"><h3>Paris Physics Master</h3></button>
</div>
<div class="field-collapse">
  <button class="field-collapse__trigger"><h3>Computer Science Master Department</h3></button>
</div>
"""


def test_sorbonne_adapter_reads_english_masters_and_reuses_existing_id() -> None:
    catalog = SorbonneAdapter(minimum_expected_programmes=2).parse_catalog(PAGE)

    assert [item.name for item in catalog.programmes] == [
        "Computer Science Master Department",
        "Paris Physics Master",
    ]
    assert catalog.programmes[0].id == "sorbonne-computer-science-master"
    assert all(item.windows == [] for item in catalog.programmes)


def test_sorbonne_adapter_rejects_a_truncated_catalogue() -> None:
    with pytest.raises(ValueError, match="expected at least 3"):
        SorbonneAdapter(minimum_expected_programmes=3).parse_catalog(PAGE)
